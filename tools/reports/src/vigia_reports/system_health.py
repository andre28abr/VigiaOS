"""Leitura consolidada da saúde do sistema para o relatório homônimo.

Lê o **último resultado** que cada ferramenta de segurança da suíte persistiu —
sem importar o código delas (Reports fica desacoplado; basta o arquivo existir):

- Hardening (Lynis)      → `/var/log/lynis-report.dat` (chave=valor; o Hardening
                            faz chown 640 pro user, então é legível).
- Antivírus (ClamAV)     → `~/.local/share/vigia-antivirus/scan-*.json`.
- Integridade (AIDE)     → `~/.config/vigia/file-integrity.json` (state).
- Rootkits               → `~/.local/share/vigia-rootkit/scans/*.json`.

Cada verificação vira `{tool, label, state, headline, detail, ran_at}` com
`state` ∈ {"ok", "warn", "danger", "missing"}. Interpretação em funções puras
(`_interpret_*`) testáveis sem I/O.
"""

from __future__ import annotations

import json
from pathlib import Path

ANTIVIRUS_DIR = Path.home() / ".local" / "share" / "vigia-antivirus"
ROOTKIT_DIR = Path.home() / ".local" / "share" / "vigia-rootkit" / "scans"
INTEGRITY_STATE = Path.home() / ".config" / "vigia" / "file-integrity.json"
LYNIS_REPORT = Path("/var/log/lynis-report.dat")


def _int(v, default: int = 0) -> int:
    try:
        return int(v)
    except (ValueError, TypeError):
        return default


def _missing(tool: str, label: str,
             detail: str = "Esta verificação ainda não foi executada.") -> dict:
    return {
        "tool": tool, "label": label, "state": "missing",
        "headline": "Nunca executada", "detail": detail, "ran_at": "—",
    }


# ============================================================
# Interpretadores puros (recebem dado já carregado)
# ============================================================


def _interpret_lynis(text: str) -> dict:
    idx = None
    ran_at = "—"
    for line in text.splitlines():
        if line.startswith("hardening_index=") and idx is None:
            idx = _int(line.split("=", 1)[1].strip(), default=-1)
        elif line.startswith("report_datetime_end="):
            ran_at = line.split("=", 1)[1].strip() or "—"
    if idx is None or idx < 0:
        return _missing("hardening", "Hardening (Lynis)")
    if idx >= 70:
        state = "ok"
    elif idx >= 50:
        state = "warn"
    else:
        state = "danger"
    return {
        "tool": "hardening", "label": "Hardening (Lynis)", "state": state,
        "headline": f"Índice de robustez: {idx}/100",
        "detail": "Auditoria de ~250 controles de segurança do sistema.",
        "ran_at": ran_at,
    }


def _interpret_antivirus(data: dict) -> dict:
    infected = _int(data.get("infected_files"))
    scanned = _int(data.get("scanned_files"))
    state = "danger" if infected > 0 else "ok"
    headline = (
        f"{infected} arquivo(s) infectado(s)" if infected
        else "Nenhuma ameaça encontrada"
    )
    return {
        "tool": "antivirus", "label": "Antivírus (ClamAV)", "state": state,
        "headline": headline,
        "detail": f"{scanned} arquivos verificados no último scan.",
        "ran_at": data.get("started_at") or "—",
    }


def _interpret_rootkit(data: dict) -> dict:
    infected = _int(data.get("infected_count"))
    warns = _int(data.get("warnings_count"))
    scanner = data.get("scanner") or "rootkit"
    if infected > 0:
        state, headline = "danger", f"{infected} indício(s) de rootkit"
    elif warns > 0:
        state, headline = "warn", f"{warns} aviso(s) a revisar"
    else:
        state, headline = "ok", "Nenhum rootkit detectado"
    return {
        "tool": "rootkit", "label": f"Rootkits ({scanner})", "state": state,
        "headline": headline,
        "detail": f"{_int(data.get('tests_run'))} testes executados.",
        "ran_at": data.get("started_at") or "—",
    }


def _interpret_file_integrity(state: dict) -> dict:
    last = state.get("last_check")
    if not state.get("baseline_exists") and not isinstance(last, dict):
        return _missing("integrity", "Integridade de arquivos (AIDE)")
    if not isinstance(last, dict):
        return {
            "tool": "integrity", "label": "Integridade de arquivos (AIDE)",
            "state": "warn", "headline": "Baseline criado, sem verificação ainda",
            "detail": "Rode uma verificação no Vigia File Integrity.", "ran_at": "—",
        }
    changed = _int(last.get("added")) + _int(last.get("removed")) + _int(last.get("changed"))
    if changed > 0:
        state_, headline = "warn", f"{changed} arquivo(s) alterado(s) desde o baseline"
    else:
        state_, headline = "ok", "Nenhuma alteração desde o baseline"
    return {
        "tool": "integrity", "label": "Integridade de arquivos (AIDE)", "state": state_,
        "headline": headline,
        "detail": f"{_int(last.get('total_entries'))} arquivos monitorados.",
        "ran_at": last.get("timestamp") or "—",
    }


# ============================================================
# Score / status / resumo (puros)
# ============================================================


def health_score(entries: list[dict]) -> dict:
    total = len(entries)
    missing = sum(1 for e in entries if e["state"] == "missing")
    ok = sum(1 for e in entries if e["state"] == "ok")
    issues = sum(1 for e in entries if e["state"] in ("warn", "danger"))
    return {"total": total, "ran": total - missing, "ok": ok,
            "issues": issues, "missing": missing}


def health_status(entries: list[dict]) -> dict:
    if any(e["state"] == "danger" for e in entries):
        return {"level": "danger", "label": "Ação necessária"}
    if any(e["state"] == "warn" for e in entries):
        return {"level": "warn", "label": "Atenção"}
    if all(e["state"] == "missing" for e in entries):
        return {"level": "warn", "label": "Sem verificações"}
    return {"level": "ok", "label": "Saudável"}


def health_summary(entries: list[dict]) -> str:
    score = health_score(entries)
    issues = [e["label"] for e in entries if e["state"] in ("warn", "danger")]
    missing = [e["label"] for e in entries if e["state"] == "missing"]
    parts = [
        f"{score['ran']} de {score['total']} verificações de segurança executadas. "
    ]
    if issues:
        parts.append(
            f"Requer atenção: {', '.join(issues[:3])}{'…' if len(issues) > 3 else ''}. "
        )
    elif score["ran"]:
        parts.append("Nenhum problema detectado nas verificações executadas. ")
    if missing:
        parts.append(
            f"Ainda não executadas: {', '.join(missing[:3])}"
            f"{'…' if len(missing) > 3 else ''} — rode as ferramentas correspondentes."
        )
    return "".join(parts)


# ============================================================
# Leitura dos arquivos (I/O) + montagem
# ============================================================


def _latest_json(dirpath: Path, pattern: str) -> dict | None:
    try:
        files = sorted(dirpath.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return None
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            return data
    return None


def read_lynis() -> dict:
    try:
        text = LYNIS_REPORT.read_text(encoding="utf-8", errors="replace") if LYNIS_REPORT.is_file() else ""
    except (OSError, PermissionError):
        text = ""
    return _interpret_lynis(text) if text else _missing("hardening", "Hardening (Lynis)")


def read_antivirus() -> dict:
    data = _latest_json(ANTIVIRUS_DIR, "scan-*.json")
    return _interpret_antivirus(data) if data else _missing("antivirus", "Antivírus (ClamAV)")


def read_rootkit() -> dict:
    data = _latest_json(ROOTKIT_DIR, "*.json")
    return _interpret_rootkit(data) if data else _missing(
        "rootkit", "Rootkits (chkrootkit/rkhunter)"
    )


def read_file_integrity() -> dict:
    state: dict = {}
    if INTEGRITY_STATE.is_file():
        try:
            loaded = json.loads(INTEGRITY_STATE.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                state = loaded
        except (OSError, json.JSONDecodeError):
            state = {}
    return _interpret_file_integrity(state)


def collect_health() -> list[dict]:
    """Uma entrada por defesa, na ordem de exibição."""
    return [read_lynis(), read_antivirus(), read_file_integrity(), read_rootkit()]
