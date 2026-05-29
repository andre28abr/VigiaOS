"""Status agregado da Vigia Suite — fonte unica de verdade.

Usado por:
- CLI `vigia status` (cli.py)
- Tooltip + item de info do tray (tray/indicator.py)

PURO PYTHON (sem GTK). Pode ser importado tanto no Hub GTK4 quanto no
subprocess GTK3 do tray, e roda headless num terminal sem display.

Custo baixo de propagacao: so `shutil.which` (binarios no PATH) + leitura
dos diretorios de relatorio (filesystem). Barato o suficiente pra rodar
no refresh periodico do tray (a cada ~2 min) sem pesar.
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import __version__
from . import backup as _backup
from .registry import TOOLS
from .settings import load_settings


# Diretorios de relatorio das tools (modulo-level pra serem mockaveis em teste)
AV_REPORTS_DIR = Path.home() / ".local" / "share" / "vigia-antivirus"
RK_REPORTS_DIR = Path.home() / ".local" / "share" / "vigia-rootkit" / "scans"

# Binarios externos "core" da suite — os scanners que de fato fazem trabalho.
# (wrapped_packages do registry inclui coisas que nao sao binarios, ex:
# 'procfs', 'coreutils', 'libcap' — por isso uma lista curada aqui.)
KEY_BINARIES = [
    "clamscan",
    "freshclam",
    "chkrootkit",
    "rkhunter",
    "aide",
    "lynis",
]


# ============================================================
# Dataclasses
# ============================================================


@dataclass
class ToolStatus:
    id: str
    name: str
    launcher: str       # ex: "vigia-antivirus"
    installed: bool


@dataclass
class BinaryStatus:
    name: str
    present: bool


@dataclass
class ScanInfo:
    kind: str           # "antivirus" | "rootkit:chkrootkit" | ...
    when_iso: str
    when_human: str     # "há 2 dias"
    clean: bool
    detail: str         # "limpo · 1234 arquivos" | "2 ameaça(s)"


@dataclass
class SuiteStatus:
    version: str = ""
    autostart: bool = False
    tray: bool = False
    lock: bool = False
    auto_lock_minutes: int = 0
    tools: list[ToolStatus] = field(default_factory=list)
    key_binaries: list[BinaryStatus] = field(default_factory=list)
    last_antivirus: ScanInfo | None = None
    last_rootkit: ScanInfo | None = None
    backups_count: int = 0
    backups_latest_human: str = ""

    @property
    def tools_total(self) -> int:
        return len(self.tools)

    @property
    def tools_available(self) -> int:
        return sum(1 for t in self.tools if t.installed)


# ============================================================
# Helpers
# ============================================================


def humanize_age(epoch: float, now: float | None = None) -> str:
    """Idade legivel em pt-BR a partir de um epoch (segundos)."""
    if not epoch or epoch <= 0:
        return "desconhecido"
    ref = now if now is not None else time.time()
    delta = int(ref - epoch)
    if delta < 0:
        delta = 0
    if delta < 60:
        return "agora mesmo"
    mins = delta // 60
    if mins < 60:
        return f"há {mins} min"
    hours = mins // 60
    if hours < 24:
        return f"há {hours} h"
    days = hours // 24
    if days < 7:
        return f"há {days} dia" + ("s" if days != 1 else "")
    weeks = days // 7
    if weeks < 5:
        return f"há {weeks} semana" + ("s" if weeks != 1 else "")
    months = days // 30
    if months < 12:
        return f"há {months} " + ("mês" if months == 1 else "meses")
    years = days // 365
    return f"há {years} ano" + ("s" if years != 1 else "")


def _iso_to_epoch(s: str) -> float:
    try:
        return datetime.fromisoformat(s).timestamp()
    except (ValueError, TypeError):
        return 0.0


def _safe_int(value: object, default: int = 0) -> int:
    """Coerce pra int sem crashar com JSON malformado (tipo errado/None).

    Os relatorios sao escritos pelas proprias tools, mas um unico arquivo
    corrompido (ex: "infected_files": "erro" ou uma lista) NAO pode derrubar
    `vigia status` (CLI) nem o refresh periodico da bandeja — ambos chamam
    gather() sem try/except em volta.
    """
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _load_json(path: Path) -> object:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def _newest_report(directory: Path, pattern: str) -> dict | None:
    """Retorna o dict do relatorio mais recente em `directory` (ou None)."""
    if not directory.is_dir():
        return None
    try:
        files = sorted(
            directory.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return None
    for f in files:
        data = _load_json(f)
        if isinstance(data, dict):
            return data
    return None


# ============================================================
# Last scans
# ============================================================


def last_antivirus_scan() -> ScanInfo | None:
    data = _newest_report(AV_REPORTS_DIR, "scan-*.json")
    if data is None:
        return None
    infected = _safe_int(data.get("infected_files"))
    scanned = _safe_int(data.get("scanned_files"))
    iso = str(data.get("started_at", ""))
    epoch = _iso_to_epoch(iso)
    clean = infected == 0
    if clean:
        detail = "limpo"
    else:
        detail = f"{infected} ameaça" + ("s" if infected != 1 else "")
    if scanned:
        detail += f" · {scanned} arquivos"
    return ScanInfo("antivirus", iso, humanize_age(epoch), clean, detail)


def last_rootkit_scan() -> ScanInfo | None:
    data = _newest_report(RK_REPORTS_DIR, "*.json")
    if data is None:
        return None
    scanner = str(data.get("scanner", "rootkit"))
    infected = _safe_int(data.get("infected_count"))
    warnings = _safe_int(data.get("warnings_count"))
    iso = str(data.get("started_at", ""))
    epoch = _iso_to_epoch(iso)
    clean = infected == 0 and warnings == 0
    if infected:
        detail = f"{infected} suspeita" + ("s" if infected != 1 else "")
    elif warnings:
        detail = f"{warnings} alerta" + ("s" if warnings != 1 else "")
    else:
        detail = "limpo"
    return ScanInfo(f"rootkit:{scanner}", iso, humanize_age(epoch), clean, detail)


# ============================================================
# Gather
# ============================================================


def gather() -> SuiteStatus:
    """Coleta o status completo da suite (barato, sincrono)."""
    s = load_settings()
    st = SuiteStatus(
        version=__version__,
        autostart=s.autostart,
        tray=s.show_tray,
        lock=s.password_lock,
        auto_lock_minutes=s.auto_lock_minutes,
    )

    for tool in TOOLS:
        launcher = tool.exec_cmd[0] if tool.exec_cmd else ""
        installed = bool(launcher) and shutil.which(launcher) is not None
        st.tools.append(ToolStatus(tool.id, tool.name, launcher, installed))

    for name in KEY_BINARIES:
        st.key_binaries.append(BinaryStatus(name, shutil.which(name) is not None))

    st.last_antivirus = last_antivirus_scan()
    st.last_rootkit = last_rootkit_scan()

    backups = _backup.list_backups()
    st.backups_count = len(backups)
    if backups:
        st.backups_latest_human = humanize_age(backups[0].get("mtime", 0))

    return st


# ============================================================
# Renderizacao
# ============================================================


def tray_tooltip(st: SuiteStatus | None = None) -> str:
    """Resumo curto de uma linha pro tooltip/info-item do tray."""
    st = st if st is not None else gather()
    parts = [f"Vigia Hub {st.version}"]
    parts.append(f"{st.tools_available}/{st.tools_total} módulos")
    av = st.last_antivirus
    if av is not None:
        head = av.detail.split(" · ", 1)[0]
        parts.append(f"antivírus {av.when_human} ({head})")
    return " · ".join(parts)


def format_text(st: SuiteStatus | None = None) -> str:
    """Render legivel pra `vigia status` (terminal)."""
    st = st if st is not None else gather()
    ok = "✓"   # ✓
    no = "✗"   # ✗
    lines: list[str] = []
    lines.append("Vigia Suite — status")
    lines.append(f"  Versão do Hub : {st.version}")

    def onoff(v: bool) -> str:
        return "ON" if v else "OFF"

    init = (
        f"autostart {onoff(st.autostart)} · "
        f"bandeja {onoff(st.tray)} · "
        f"bloqueio {onoff(st.lock)}"
    )
    if st.lock and st.auto_lock_minutes > 0:
        init += f" · auto-lock {st.auto_lock_minutes}min"
    lines.append(f"  Inicialização : {init}")

    lines.append("")
    lines.append(f"  Módulos ({st.tools_available}/{st.tools_total} disponíveis):")
    for t in st.tools:
        mark = ok if t.installed else no
        lines.append(f"    [{mark}] {t.name:<26} {t.launcher}")

    lines.append("")
    lines.append("  Ferramentas externas:")
    for b in st.key_binaries:
        mark = ok if b.present else no
        lines.append(f"    [{mark}] {b.name}")

    lines.append("")
    av = st.last_antivirus
    if av is not None:
        lines.append(f"  Último scan antivírus : {av.when_human} — {av.detail}")
    else:
        lines.append("  Último scan antivírus : nunca")
    rk = st.last_rootkit
    if rk is not None:
        lines.append(f"  Último scan rootkit   : {rk.when_human} — {rk.detail}")
    else:
        lines.append("  Último scan rootkit   : nunca")

    if st.backups_count:
        lines.append(
            f"  Backups               : {st.backups_count} "
            f"(mais recente {st.backups_latest_human})"
        )
    else:
        lines.append("  Backups               : nenhum")

    return "\n".join(lines)


def to_dict(st: SuiteStatus | None = None) -> dict:
    """Serializa pra JSON (`vigia status --json`)."""
    st = st if st is not None else gather()

    def scan(s: ScanInfo | None) -> dict | None:
        if s is None:
            return None
        return {
            "kind": s.kind,
            "when": s.when_iso,
            "when_human": s.when_human,
            "clean": s.clean,
            "detail": s.detail,
        }

    return {
        "version": st.version,
        "settings": {
            "autostart": st.autostart,
            "tray": st.tray,
            "lock": st.lock,
            "auto_lock_minutes": st.auto_lock_minutes,
        },
        "tools_available": st.tools_available,
        "tools_total": st.tools_total,
        "tools": [
            {"id": t.id, "name": t.name, "launcher": t.launcher,
             "installed": t.installed}
            for t in st.tools
        ],
        "key_binaries": [
            {"name": b.name, "present": b.present} for b in st.key_binaries
        ],
        "last_antivirus": scan(st.last_antivirus),
        "last_rootkit": scan(st.last_rootkit),
        "backups_count": st.backups_count,
        "backups_latest_human": st.backups_latest_human,
    }
