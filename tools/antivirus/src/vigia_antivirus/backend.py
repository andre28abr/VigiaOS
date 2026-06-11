"""Backend ClamAV.

Operacoes:
- clamav_installed() -> bool
- get_db_info() -> DbInfo (versao, ultima atualizacao, signatures)
- daemon_running() -> bool
- update_db_blocking() -> (ok, err)  [pkexec freshclam]
- scan_blocking(path, recursive) -> ScanResult
- scan_async(path, on_progress, on_done) -> ScanHandle

Reports salvos em ~/.local/share/vigia-antivirus/ com mode 0600 (LGPD).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from vigia_common.state import save_json_0600


REPORTS_DIR = Path.home() / ".local" / "share" / "vigia-antivirus"


@dataclass
class DbInfo:
    engine_version: str = ""
    db_version: str = ""
    sig_count: int = 0
    last_update: str = ""        # texto human-readable
    last_update_epoch: int = 0
    db_dir: str = ""


@dataclass
class Finding:
    path: str
    signature: str               # ex: "Eicar-Signature.UNOFFICIAL"


@dataclass
class ScanResult:
    target: str
    findings: list[Finding] = field(default_factory=list)
    scanned_files: int = 0
    scanned_dirs: int = 0
    infected_files: int = 0
    data_scanned: str = ""       # ex: "12.34 MB"
    elapsed_sec: float = 0.0
    raw_summary: str = ""
    error: str = ""
    started_at: str = ""         # ISO timestamp


# ============================================================
# Sanity
# ============================================================


def clamav_installed() -> bool:
    return shutil.which("clamscan") is not None


def freshclam_installed() -> bool:
    return shutil.which("freshclam") is not None


def daemon_running() -> bool:
    """Verifica se clamd/clamav-daemon esta ativo (sem pkexec)."""
    if shutil.which("systemctl") is None:
        return False
    for unit in ("clamd@scan", "clamav-daemon", "clamd"):
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "--quiet", unit],
                timeout=5,
            )
            if result.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    return False


# Subprocesso centralizado em vigia_common.proc.run (nunca levanta;
# timeout/binário ausente -> (1, "", "")). Aliased p/ não mexer nos callers.
from vigia_common.proc import run as _run


# ============================================================
# DB info
# ============================================================


# Dirs onde a base de assinaturas pode estar (1ª que existir vence).
DB_DIRS = (
    "/var/lib/clamav",
    "/usr/local/share/clamav",
    "/var/lib/clamav-unofficial-sigs",
)


def _newest_db_mtime(db_dir: Path) -> float | None:
    """mtime do arquivo de assinatura (.cvd/.cld) mais recente em `db_dir`.

    Retorna None se o dir não tiver base legível. É a fonte de idade do Vigia
    porque é **independente de locale** — ao contrário da data no
    `clamscan --version`, cujo `strptime("%a %b …")` quebra sob locale pt-BR
    (espera "Dom"/"Jun" e recebe o inglês "Sun"/"Jun" do ClamAV).
    """
    newest: float | None = None
    try:
        for f in db_dir.glob("*.c[lv]d"):  # daily/main/bytecode .cvd ou .cld
            try:
                m = f.stat().st_mtime
            except OSError:
                continue
            if newest is None or m > newest:
                newest = m
    except OSError:
        return None
    return newest


def get_db_info(db_dirs: tuple[str, ...] | None = None) -> DbInfo:
    info = DbInfo()
    if not clamav_installed():
        return info

    # Versão do engine + versão da base via `clamscan --version`:
    #   "ClamAV 1.4.4/27600/Sun Jun  1 03:30:00 2026"
    # NÃO usamos o 3º campo (data) pra idade: o strptime dele é locale-dependent
    # e nem sempre vem preenchido. A idade sai do mtime dos arquivos (abaixo).
    rc, out, _ = _run(["clamscan", "--version"], timeout=10)
    if rc == 0 and out:
        parts = out.strip().split("/")
        if parts:
            m = re.search(r"ClamAV\s+([\d.]+)", parts[0])
            if m:
                info.engine_version = m.group(1)
        if len(parts) >= 2:
            info.db_version = parts[1].strip()

    # Idade / última atualização pela mtime do arquivo de base mais recente.
    for candidate in (db_dirs or DB_DIRS):
        d = Path(candidate)
        if not d.is_dir():
            continue
        if not info.db_dir:
            info.db_dir = candidate
        newest = _newest_db_mtime(d)
        if newest is not None:
            info.last_update_epoch = int(newest)
            # strftime só com códigos numéricos (%d/%m/%Y %H:%M) — sem %a/%b,
            # portanto também independente de locale.
            info.last_update = datetime.fromtimestamp(newest).strftime(
                "%d/%m/%Y %H:%M"
            )
            break

    return info


def db_age_days(info: DbInfo) -> int | None:
    """Retorna idade da base em dias, ou None se desconhecido."""
    if info.last_update_epoch <= 0:
        return None
    now = int(time.time())
    return (now - info.last_update_epoch) // 86400


# ============================================================
# Update DB (freshclam)
# ============================================================


def update_db_blocking() -> tuple[bool, str]:
    """`pkexec freshclam`. Atualiza base de assinaturas."""
    if not freshclam_installed():
        return False, "freshclam não instalado (pacote clamav-update)."
    if shutil.which("pkexec") is None:
        return False, "pkexec não encontrado."

    rc, out, err = _run(["pkexec", "freshclam"], timeout=300)
    if rc in (126, 127):
        return False, "Autenticação cancelada."
    # freshclam pode retornar 0 (atualizado) ou 1 (ja atualizado)
    if rc not in (0, 1):
        msg = (err or out).strip()
        return False, f"Falha ao atualizar base:\n\n{msg[:600]}"
    return True, ""


# ============================================================
# Scan
# ============================================================


def _ensure_reports_dir() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(REPORTS_DIR, 0o700)
    except OSError:
        pass
    return REPORTS_DIR


def _save_report(result: ScanResult) -> None:
    """Salva resultado em ~/.local/share/vigia-antivirus/<timestamp>.json com 0600."""
    if not result.started_at:
        return
    rd = _ensure_reports_dir()
    safe_ts = result.started_at.replace(":", "-").replace(".", "_")
    path = rd / f"scan-{safe_ts}.json"
    data = {
        "target": result.target,
        "started_at": result.started_at,
        "scanned_files": result.scanned_files,
        "scanned_dirs": result.scanned_dirs,
        "infected_files": result.infected_files,
        "data_scanned": result.data_scanned,
        "elapsed_sec": result.elapsed_sec,
        "findings": [{"path": f.path, "signature": f.signature} for f in result.findings],
    }
    save_json_0600(path, data)


def list_recent_reports(limit: int = 10) -> list[dict]:
    """Lista reports recentes (mais novos primeiro)."""
    rd = REPORTS_DIR
    if not rd.is_dir():
        return []
    files = sorted(rd.glob("scan-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for f in files[:limit]:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        # HARDENING: report corrompido pode nao ser dict — pula.
        if not isinstance(data, dict):
            continue
        data["_file"] = str(f)
        out.append(data)
    return out


def scan_async(
    path: str,
    on_line: Callable[[str], None],
    on_done: Callable[[ScanResult], None],
    stop_flag: Callable[[], bool] | None = None,
) -> threading.Thread:
    """Roda clamscan e streama lines via on_line.

    Args:
        path: caminho a escanear.
        on_line: callback por linha de stdout (thread do worker — chame
                 GLib.idle_add para tocar a UI).
        on_done: callback quando termina com ScanResult.
        stop_flag: callable retornando True se deve cancelar.

    Retorna a Thread iniciada (pode esperar ou ignorar).
    """
    def worker():
        result = ScanResult(target=path)
        result.started_at = datetime.now().isoformat(timespec="seconds")

        if not clamav_installed():
            result.error = "clamscan não instalado."
            on_done(result)
            return
        if not Path(path).exists():
            result.error = f"Caminho não existe: {path}"
            on_done(result)
            return

        # Escolha: clamdscan se daemon ativo (mais rapido), senao clamscan.
        # clamdscan tem flags ligeiramente diferentes; uso clamscan por
        # consistencia + suporte universal nesta v0.1.
        # NOTA: `--no-summary`/`--bell` sao flags booleanas do clamscan e NAO
        # aceitam `=valor` (passar `--no-summary=no` faz o clamscan abortar
        # antes de escanear). O summary (que o parser abaixo precisa) vem por
        # padrao; o bell ja' e' off por padrao. Por isso so' `-r`.
        cmd = ["clamscan", "-r"]
        # Varredura de sistema inteiro ("/"): pula pseudo-filesystems que
        # nao contem arquivos reais (e que poderiam travar/poluir o scan).
        if os.path.abspath(path) == "/":
            for pat in ("^/proc", "^/sys", "^/dev", "^/run"):
                cmd.append(f"--exclude-dir={pat}")
        # `--` encerra as flags: path do usuario comecando com `-` nao vira flag.
        cmd.extend(["--", path])

        start = time.time()
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except (OSError, FileNotFoundError) as e:
            result.error = f"Falha ao iniciar scan: {e}"
            on_done(result)
            return

        try:
            in_summary = False
            for raw_line in proc.stdout or []:
                if stop_flag is not None and stop_flag():
                    proc.terminate()
                    result.error = "Scan cancelado pelo usuário."
                    break

                line = raw_line.rstrip()
                on_line(line)

                # Findings: linhas no formato "<path>: <SIGNATURE> FOUND"
                m = re.match(r"^(.+):\s+(\S+)\s+FOUND\s*$", line)
                if m:
                    result.findings.append(Finding(path=m.group(1), signature=m.group(2)))
                    continue

                # Summary parsing
                if line.startswith("----------- SCAN SUMMARY"):
                    in_summary = True
                    continue
                if in_summary:
                    if line.startswith("Scanned directories:"):
                        result.scanned_dirs = int(_extract_int(line))
                    elif line.startswith("Scanned files:"):
                        result.scanned_files = int(_extract_int(line))
                    elif line.startswith("Infected files:"):
                        result.infected_files = int(_extract_int(line))
                    elif line.startswith("Data scanned:"):
                        result.data_scanned = line.partition(":")[2].strip()
                    result.raw_summary += line + "\n"

            proc.wait(timeout=10)
        except (OSError, subprocess.TimeoutExpired) as e:
            if not result.error:
                result.error = f"Erro durante scan: {e}"

        result.elapsed_sec = round(time.time() - start, 2)

        # ClamAV exit codes: 0 (clean), 1 (infected found), 2 (error).
        # Tratamos 0 e 1 como sucesso de execucao. Num scan de sistema
        # inteiro como usuario comum, "Permission denied" em arquivos de
        # outros donos tambem gera rc=2 — nao e' fatal se o scan rodou de
        # fato (algum arquivo foi lido).
        if (
            proc.returncode == 2
            and not result.error
            and result.scanned_files == 0
        ):
            result.error = "ClamAV reportou erro de execução (rc=2)."

        if not result.error:
            _save_report(result)
            try:
                from vigia_common.events import record
                n = len(result.findings)
                record("antivirus",
                       f"Varredura: {n} ameaça(s) em "
                       f"{result.scanned_files} arquivo(s)",
                       category="scan", severity=("high" if n else "ok"),
                       ref=result.target,
                       payload={"infected": n, "files": result.scanned_files})
                for f in result.findings:
                    record("antivirus", f.signature, category="finding",
                           severity="high", ref=f.path,
                           payload={"signature": f.signature})
            except Exception:  # pylint: disable=broad-except
                pass
        on_done(result)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t


def _extract_int(line: str) -> int:
    m = re.search(r"\d+", line)
    return int(m.group(0)) if m else 0
