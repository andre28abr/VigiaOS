"""Backend rootkit scanners — wrappa chkrootkit + rkhunter via pkexec.

Operacoes:
- chkrootkit_installed() / rkhunter_installed() -> bool
- get_versions() -> Versions (chkrootkit + rkhunter)
- scan_chkrootkit_async(on_line, on_done, stop_flag) -> Thread
- scan_rkhunter_async(on_line, on_done, stop_flag) -> Thread
- list_recent_reports(limit) -> list[dict]
- load_report(path) -> dict

Reports salvos em ~/.local/share/vigia-rootkit/scans/ com mode 0600 (LGPD).
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


REPORTS_DIR = Path.home() / ".local" / "share" / "vigia-rootkit" / "scans"


@dataclass
class Versions:
    chkrootkit: str = ""
    rkhunter: str = ""


@dataclass
class Finding:
    test: str
    severity: str
    detail: str
    line: str = ""


@dataclass
class ScanResult:
    scanner: str
    findings: list[Finding] = field(default_factory=list)
    tests_run: int = 0
    warnings_count: int = 0
    infected_count: int = 0
    elapsed_sec: float = 0.0
    error: str = ""
    cancelled: bool = False
    started_at: str = ""
    raw_output: str = ""


# ============================================================
# Sanity
# ============================================================


def chkrootkit_installed() -> bool:
    return shutil.which("chkrootkit") is not None


def rkhunter_installed() -> bool:
    return shutil.which("rkhunter") is not None


# Subprocesso centralizado em vigia_common.proc.run (nunca levanta;
# timeout/binário ausente -> (1, "", "")). Aliased p/ não mexer nos callers.
from vigia_common.proc import run as _run


def get_versions() -> Versions:
    v = Versions()
    if chkrootkit_installed():
        rc, out, err = _run(["chkrootkit", "-V"], timeout=5)
        text = (err or out).strip()
        m = re.search(r"version\s+(\S+)", text, re.IGNORECASE)
        if m:
            v.chkrootkit = m.group(1)
    if rkhunter_installed():
        rc, out, _ = _run(["rkhunter", "--version"], timeout=5)
        for line in (out or "").splitlines():
            m = re.search(r"Rootkit Hunter\s+(\S+)", line)
            if m:
                v.rkhunter = m.group(1)
                break
    return v


# ============================================================
# Reports (history)
# ============================================================


def _ensure_reports_dir() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(REPORTS_DIR, 0o700)
    except OSError:
        pass
    return REPORTS_DIR


def _save_report(result: ScanResult) -> Path | None:
    if not result.started_at:
        return None
    rd = _ensure_reports_dir()
    safe_ts = result.started_at.replace(":", "-").replace(".", "_")
    path = rd / f"{result.scanner}-{safe_ts}.json"
    data = {
        "scanner": result.scanner,
        "started_at": result.started_at,
        "tests_run": result.tests_run,
        "warnings_count": result.warnings_count,
        "infected_count": result.infected_count,
        "elapsed_sec": result.elapsed_sec,
        "cancelled": result.cancelled,
        "error": result.error,
        "findings": [
            {"test": f.test, "severity": f.severity, "detail": f.detail}
            for f in result.findings
        ],
        "raw_output": result.raw_output[:256_000],
    }
    return path if save_json_0600(path, data) else None


def list_recent_reports(limit: int = 20) -> list[dict]:
    if not REPORTS_DIR.is_dir():
        return []
    files = sorted(
        REPORTS_DIR.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
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


def load_report(path: str) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    # HARDENING: garante dict (ou None) pro caller.
    return data if isinstance(data, dict) else None


# ============================================================
# Parsers
# ============================================================


_CHKR_TEST_RE = re.compile(r"^Checking\s+`?([^'`]+)'?\.{3}\s*(.*)$")


def _parse_chkrootkit_line(line: str) -> Finding | None:
    m = _CHKR_TEST_RE.match(line.strip())
    if not m:
        return None
    test, status = m.group(1), m.group(2).strip()
    status_lower = status.lower()
    if "infected" in status_lower and "not infected" not in status_lower:
        return Finding(test=test, severity="INFECTED", detail=status, line=line)
    if "you have" in status_lower or "warning" in status_lower:
        return Finding(test=test, severity="WARNING", detail=status, line=line)
    if "vulnerable" in status_lower:
        return Finding(test=test, severity="WARNING", detail=status, line=line)
    return None


_RKH_BRACKET_RE = re.compile(r"^(.+?)\s+\[\s*(\S+)\s*\]\s*$")


def _parse_rkhunter_line(line: str) -> Finding | None:
    s = line.strip()
    if not s:
        return None
    m = _RKH_BRACKET_RE.match(s)
    if m:
        test, status = m.group(1).strip(), m.group(2).strip()
        if status.lower() == "warning":
            return Finding(test=test, severity="WARNING", detail=status, line=line)
        if status.lower() in ("infected", "compromised"):
            return Finding(test=test, severity="INFECTED", detail=status, line=line)
        return None
    if s.startswith("Warning:"):
        return Finding(
            test="rkhunter-warning", severity="WARNING",
            detail=s[len("Warning:"):].strip(), line=line,
        )
    return None


# ============================================================
# Scans (async, streaming via pkexec)
# ============================================================


_MAX_RAW_OUTPUT_BYTES = 1_000_000


def _run_scan_streaming(
    scanner_name: str,
    cmd: list[str],
    parser: Callable[[str], Finding | None],
    on_line: Callable[[str], None],
    on_done: Callable[[ScanResult], None],
    stop_flag: Callable[[], bool] | None,
) -> None:
    result = ScanResult(scanner=scanner_name)
    result.started_at = datetime.now().isoformat(timespec="seconds")
    start = time.time()

    if shutil.which("pkexec") is None:
        result.error = "pkexec não encontrado."
        on_done(result)
        return

    try:
        proc = subprocess.Popen(
            ["pkexec"] + cmd,
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
        for raw_line in proc.stdout or []:
            if stop_flag is not None and stop_flag():
                proc.terminate()
                result.cancelled = True
                result.error = "Scan cancelado pelo usuário."
                break
            line = raw_line.rstrip()
            on_line(line)
            if len(result.raw_output) < _MAX_RAW_OUTPUT_BYTES:
                result.raw_output += line + "\n"
            if line.strip().startswith("Checking"):
                result.tests_run += 1
            finding = parser(line)
            if finding is not None:
                result.findings.append(finding)
                if finding.severity == "INFECTED":
                    result.infected_count += 1
                elif finding.severity == "WARNING":
                    result.warnings_count += 1
        proc.wait(timeout=10)
    except (OSError, subprocess.TimeoutExpired) as e:
        if not result.error:
            result.error = f"Erro durante scan: {e}"

    if proc.returncode in (126, 127) and not result.cancelled:
        result.error = "Autenticação cancelada (pkexec)."
        result.cancelled = True

    result.elapsed_sec = round(time.time() - start, 2)

    if not result.cancelled and not result.error:
        _save_report(result)
        try:
            from vigia_common.events import record
            worst = ("high" if result.infected_count
                     else ("medium" if result.warnings_count else "ok"))
            record("rootkit",
                   f"{result.scanner}: {result.infected_count} infectado(s), "
                   f"{result.warnings_count} aviso(s)",
                   category="scan", severity=worst, ref=result.scanner,
                   payload={"infected": result.infected_count,
                            "warnings": result.warnings_count})
            for f in result.findings:
                sev = "high" if str(f.severity).upper() == "INFECTED" else "medium"
                record("rootkit", f.test, category="finding", severity=sev,
                       detail=f.detail, ref=result.scanner,
                       payload={"severity": f.severity})
        except Exception:  # pylint: disable=broad-except
            pass

    on_done(result)


def scan_chkrootkit_async(
    on_line: Callable[[str], None],
    on_done: Callable[[ScanResult], None],
    stop_flag: Callable[[], bool] | None = None,
) -> threading.Thread:
    def worker():
        if not chkrootkit_installed():
            r = ScanResult(
                scanner="chkrootkit",
                started_at=datetime.now().isoformat(timespec="seconds"),
                error="chkrootkit não instalado.",
            )
            on_done(r)
            return
        _run_scan_streaming(
            scanner_name="chkrootkit",
            cmd=["chkrootkit"],
            parser=_parse_chkrootkit_line,
            on_line=on_line,
            on_done=on_done,
            stop_flag=stop_flag,
        )
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t


def scan_rkhunter_async(
    on_line: Callable[[str], None],
    on_done: Callable[[ScanResult], None],
    stop_flag: Callable[[], bool] | None = None,
) -> threading.Thread:
    def worker():
        if not rkhunter_installed():
            r = ScanResult(
                scanner="rkhunter",
                started_at=datetime.now().isoformat(timespec="seconds"),
                error="rkhunter não instalado.",
            )
            on_done(r)
            return
        _run_scan_streaming(
            scanner_name="rkhunter",
            cmd=[
                "rkhunter", "--check",
                "--skip-keypress",
                "--no-mail-on-warning",
                "--rwo",
            ],
            parser=_parse_rkhunter_line,
            on_line=on_line,
            on_done=on_done,
            stop_flag=stop_flag,
        )
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t
