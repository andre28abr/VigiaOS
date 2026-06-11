"""Banco de eventos do VigiaOS — fonte da verdade pra a Central de Relatórios.

Armazena os ACHADOS das ferramentas (antivírus, rootkit, vuln, hardening…) e
alertas num **SQLite local** (`~/.local/share/vigia/events.db`, 0600), pra depois
gerar relatórios **por período**. Sem servidor, sem daemon — só a stdlib
`sqlite3`. Casa com o "mínima superfície" e a LGPD (local, 0600/0700, retenção).

Filosofia de robustez: **nunca derruba quem chama**. As ferramentas chamam
`record()` ao achar algo; se o banco falhar, `record()` devolve `None` (e a
ferramenta segue normal). `query()` devolve `[]` em erro.

API principal:
- `record(source, title, …)` — grava um evento; devolve o id (ou None).
- `query(start=…, end=…, sources=…, severities=…, …)` — lê eventos filtrados.
- `summary(start, end)` / `counts_by_day(...)` — agregações pra relatório.
- `prune(dias)` / `purge_all()` — retenção / "limpar histórico".

Severidade é **normalizada** (PT/EN → conjunto canônico) pra os relatórios
agregarem de forma consistente — ver `normalize_severity`.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional, Union

# ~/.local/share/vigia/events.db (compartilhado por todo o ecossistema)
DB_PATH = Path.home() / ".local" / "share" / "vigia" / "events.db"

# Retenção padrão: curta (minimização de dados — LGPD). Configurável.
DEFAULT_RETENTION_DAYS = 180

# Severidades canônicas, da pior pra menos grave.
CANON_SEVERITIES = ["critical", "high", "medium", "low", "info", "ok", "unknown"]
SEVERITY_RANK = {s: i for i, s in enumerate(CANON_SEVERITIES)}

# Sinônimos (PT/EN) -> canônica.
_SEV_MAP = {
    "critical": "critical", "crítico": "critical", "critico": "critical",
    "high": "high", "alto": "high", "alta": "high",
    "error": "high", "erro": "high",
    "medium": "medium", "médio": "medium", "medio": "medium",
    "média": "medium", "media": "medium", "moderado": "medium",
    "suspeito": "medium", "warning": "medium", "aviso": "medium",
    "atenção": "medium", "atencao": "medium",
    "low": "low", "baixo": "low", "baixa": "low",
    "info": "info", "informativo": "info", "informational": "info",
    "information": "info", "teste": "info", "notice": "info",
    "ok": "ok", "limpo": "ok", "clean": "ok", "pass": "ok",
    "passed": "ok", "success": "ok", "sucesso": "ok",
}

_Timeish = Union[datetime, int, float, str, None]


def normalize_severity(s: object) -> str:
    """Mapeia uma severidade (PT/EN) pra o conjunto canônico.

    Conhecidas viram a canônica (ex.: "Alto"/"high" -> "high"). Desconhecida
    não-vazia é preservada (minúscula); vazia vira "unknown".
    """
    key = str(s or "").strip().lower()
    if not key:
        return "unknown"
    return _SEV_MAP.get(key, key)


def severity_rank(s: object) -> int:
    """Posição da severidade pra ordenar (pior primeiro). Desconhecida vai pro fim."""
    return SEVERITY_RANK.get(normalize_severity(s), len(CANON_SEVERITIES))


@dataclass(frozen=True)
class Event:
    """Um evento registrado."""

    id: int
    ts: str            # ISO local, legível
    ts_epoch: float    # unix seconds (índice/ordenação)
    source: str        # ferramenta que gerou (ex.: "antivirus")
    category: str      # tipo (ex.: "scan", "finding", "alert", "status")
    severity: str      # canônica
    title: str
    detail: str = ""
    ref: str = ""      # alvo/arquivo/CVE/host…
    payload: dict = field(default_factory=dict)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        TEXT NOT NULL,
    ts_epoch  REAL NOT NULL,
    source    TEXT NOT NULL,
    category  TEXT NOT NULL DEFAULT 'finding',
    severity  TEXT NOT NULL DEFAULT 'info',
    title     TEXT NOT NULL,
    detail    TEXT NOT NULL DEFAULT '',
    ref       TEXT NOT NULL DEFAULT '',
    payload   TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts_epoch);
CREATE INDEX IF NOT EXISTS idx_events_source ON events(source);
CREATE INDEX IF NOT EXISTS idx_events_severity ON events(severity);
"""

_COLS = "id, ts, ts_epoch, source, category, severity, title, detail, ref, payload"


# ============================================================
# Conexão / esquema (privado)
# ============================================================


def _connect(db_path: Optional[Union[str, Path]]) -> Optional[sqlite3.Connection]:
    """Abre (e cria, 0600) o banco. Devolve None em falha — nunca levanta."""
    try:
        p = Path(db_path) if db_path is not None else DB_PATH
        p.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(p.parent, 0o700)
        except OSError:
            pass
        if not p.exists():
            # cria já com 0600 (não deixa janela com permissão default).
            fd = os.open(str(p), os.O_CREAT | os.O_WRONLY, 0o600)
            os.close(fd)
        conn = sqlite3.connect(str(p))
        conn.execute("PRAGMA busy_timeout=3000")
        conn.executescript(_SCHEMA)
        try:
            os.chmod(p, 0o600)
        except OSError:
            pass
        return conn
    except (sqlite3.Error, OSError, ValueError):
        return None


def _to_epoch(when: _Timeish) -> float:
    if isinstance(when, bool):           # bool é int — barra antes
        return 0.0
    if isinstance(when, (int, float)):
        return float(when)
    if isinstance(when, datetime):
        return when.timestamp()
    if isinstance(when, str):
        try:
            return datetime.fromisoformat(when).timestamp()
        except ValueError:
            return 0.0
    return 0.0


def _row_to_event(r: tuple) -> Event:
    try:
        payload = json.loads(r[9]) if r[9] else {}
    except (ValueError, TypeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    return Event(
        id=r[0], ts=r[1], ts_epoch=r[2], source=r[3], category=r[4],
        severity=r[5], title=r[6], detail=r[7], ref=r[8], payload=payload,
    )


# ============================================================
# Escrita
# ============================================================


def record(
    source: str,
    title: str,
    *,
    category: str = "finding",
    severity: object = "info",
    detail: str = "",
    ref: str = "",
    payload: Optional[dict] = None,
    ts: Optional[datetime] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[int]:
    """Grava um evento. Devolve o id, ou **None** em erro (nunca levanta).

    `source` = ferramenta ("antivirus", "vuln"…). `severity` é normalizada.
    `payload` = dados extras (dict, vira JSON). `ts` = quando (default: agora).
    """
    if not source or not title:
        return None
    conn = _connect(db_path)
    if conn is None:
        return None
    try:
        when = ts if isinstance(ts, datetime) else datetime.now()
        try:
            pl = json.dumps(payload or {}, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            pl = "{}"
        cur = conn.execute(
            f"INSERT INTO events ({_COLS[4:]}) "  # pula "id, " (autoincrement)
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (when.isoformat(timespec="seconds"), when.timestamp(),
             str(source), str(category), normalize_severity(severity),
             str(title), str(detail), str(ref), pl),
        )
        conn.commit()
        return cur.lastrowid
    except (sqlite3.Error, ValueError, OSError):
        return None
    finally:
        conn.close()


# ============================================================
# Leitura / consulta
# ============================================================


def query(
    *,
    start: _Timeish = None,
    end: _Timeish = None,
    sources: Optional[Iterable[str]] = None,
    severities: Optional[Iterable[str]] = None,
    categories: Optional[Iterable[str]] = None,
    search: str = "",
    limit: int = 1000,
    db_path: Optional[Union[str, Path]] = None,
) -> list[Event]:
    """Eventos filtrados, mais novos primeiro. Devolve [] em erro.

    `start`/`end` aceitam datetime, epoch (número) ou ISO string. `sources`/
    `severities`/`categories` são listas. `search` casa em título/detalhe/ref.
    """
    conn = _connect(db_path)
    if conn is None:
        return []
    try:
        where: list[str] = []
        params: list[object] = []
        if start is not None:
            where.append("ts_epoch >= ?")
            params.append(_to_epoch(start))
        if end is not None:
            where.append("ts_epoch <= ?")
            params.append(_to_epoch(end))
        srcs = list(sources or [])
        if srcs:
            where.append(f"source IN ({','.join('?' * len(srcs))})")
            params += srcs
        sevs = [normalize_severity(s) for s in (severities or [])]
        if sevs:
            where.append(f"severity IN ({','.join('?' * len(sevs))})")
            params += sevs
        cats = list(categories or [])
        if cats:
            where.append(f"category IN ({','.join('?' * len(cats))})")
            params += cats
        if search:
            where.append("(title LIKE ? OR detail LIKE ? OR ref LIKE ?)")
            like = f"%{search}%"
            params += [like, like, like]

        sql = f"SELECT {_COLS} FROM events"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY ts_epoch DESC, id DESC"
        if limit and limit > 0:
            sql += " LIMIT ?"
            params.append(int(limit))
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_event(r) for r in rows]
    except (sqlite3.Error, ValueError):
        return []
    finally:
        conn.close()


def count(db_path: Optional[Union[str, Path]] = None) -> int:
    """Total de eventos guardados."""
    conn = _connect(db_path)
    if conn is None:
        return 0
    try:
        return int(conn.execute("SELECT COUNT(*) FROM events").fetchone()[0])
    except sqlite3.Error:
        return 0
    finally:
        conn.close()


def distinct_sources(db_path: Optional[Union[str, Path]] = None) -> list[str]:
    """Ferramentas que já gravaram eventos (pra filtros)."""
    conn = _connect(db_path)
    if conn is None:
        return []
    try:
        rows = conn.execute(
            "SELECT DISTINCT source FROM events ORDER BY source").fetchall()
        return [r[0] for r in rows]
    except sqlite3.Error:
        return []
    finally:
        conn.close()


# ============================================================
# Agregações (pra a Central de Relatórios)
# ============================================================


def _where_period(start: _Timeish, end: _Timeish) -> tuple[str, list]:
    where, params = [], []
    if start is not None:
        where.append("ts_epoch >= ?")
        params.append(_to_epoch(start))
    if end is not None:
        where.append("ts_epoch <= ?")
        params.append(_to_epoch(end))
    return (" WHERE " + " AND ".join(where)) if where else "", params


def summary(
    *,
    start: _Timeish = None,
    end: _Timeish = None,
    db_path: Optional[Union[str, Path]] = None,
) -> dict:
    """Resumo do período: total + contagem por fonte e por severidade."""
    base = {"total": 0, "by_source": {}, "by_severity": {}}
    conn = _connect(db_path)
    if conn is None:
        return base
    try:
        wsql, params = _where_period(start, end)
        total = conn.execute(
            f"SELECT COUNT(*) FROM events{wsql}", params).fetchone()[0]
        by_source = dict(conn.execute(
            f"SELECT source, COUNT(*) FROM events{wsql} GROUP BY source",
            params).fetchall())
        by_sev = dict(conn.execute(
            f"SELECT severity, COUNT(*) FROM events{wsql} GROUP BY severity",
            params).fetchall())
        return {"total": int(total), "by_source": by_source, "by_severity": by_sev}
    except sqlite3.Error:
        return base
    finally:
        conn.close()


def counts_by_day(
    *,
    start: _Timeish = None,
    end: _Timeish = None,
    db_path: Optional[Union[str, Path]] = None,
) -> list[tuple[str, int]]:
    """Contagem por dia (YYYY-MM-DD, local) — base pra gráfico de linha do tempo."""
    conn = _connect(db_path)
    if conn is None:
        return []
    try:
        wsql, params = _where_period(start, end)
        rows = conn.execute(
            "SELECT strftime('%Y-%m-%d', ts_epoch, 'unixepoch', 'localtime') AS d, "
            f"COUNT(*) FROM events{wsql} GROUP BY d ORDER BY d",
            params).fetchall()
        return [(r[0], int(r[1])) for r in rows]
    except sqlite3.Error:
        return []
    finally:
        conn.close()


# ============================================================
# Retenção / limpeza (LGPD)
# ============================================================


def prune(
    older_than_days: int = DEFAULT_RETENTION_DAYS,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Apaga eventos mais velhos que `older_than_days`. Devolve quantos saíram."""
    conn = _connect(db_path)
    if conn is None:
        return 0
    try:
        cutoff = (datetime.now() - timedelta(days=max(0, older_than_days))).timestamp()
        cur = conn.execute("DELETE FROM events WHERE ts_epoch < ?", (cutoff,))
        conn.commit()
        return cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
    except sqlite3.Error:
        return 0
    finally:
        conn.close()


def purge_all(db_path: Optional[Union[str, Path]] = None) -> int:
    """Apaga TODOS os eventos ("limpar histórico"). Devolve quantos saíram."""
    conn = _connect(db_path)
    if conn is None:
        return 0
    try:
        n = int(conn.execute("SELECT COUNT(*) FROM events").fetchone()[0])
        conn.execute("DELETE FROM events")
        conn.commit()
        return n
    except sqlite3.Error:
        return 0
    finally:
        conn.close()
