"""Backend AIDE.

Operacoes:
- baseline_status() -> verifica /var/lib/aide/aide.db.gz
- run_init_blocking() -> aide --init && mv aide.db.new.gz aide.db.gz
- run_check_blocking() -> aide --check (returncode 0 = sem mudancas, 1+ = mudancas)
- run_update_blocking() -> aide --update + move db.new -> db
- parse_check_output() -> CheckResult com summary + listas de added/removed/changed

Todas as operacoes que mexem em /var/lib/aide/ precisam de root → via pkexec.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field

from vigia_common.platform import install_hint
from vigia_common.state import load_json, save_json_0600
from datetime import datetime
from pathlib import Path


# ============================================================
# Paths: o Vigia File Integrity usa o config padrao do AIDE no Fedora
# Workstation — /etc/aide.conf + /var/lib/aide/aide.db.gz. Esse perfil
# monitora /usr, /sbin, /boot, /etc etc (cobertura completa do sistema
# mutavel do Workstation).
# ============================================================

AIDE_DB_SYSTEM = Path("/var/lib/aide/aide.db.gz")
AIDE_DB_NEW_SYSTEM = Path("/var/lib/aide/aide.db.new.gz")
AIDE_CONF_SYSTEM = Path("/etc/aide.conf")

# Aliases mantidos para compatibilidade
AIDE_DB = AIDE_DB_SYSTEM
AIDE_DB_NEW = AIDE_DB_NEW_SYSTEM
AIDE_CONF = AIDE_CONF_SYSTEM

# Cache local de metadata (ultimo check, summary, etc.)
STATE_DIR = Path.home() / ".config" / "vigia"
STATE_FILE = STATE_DIR / "file-integrity.json"


@dataclass
class CheckSummary:
    total_entries: int = 0
    added: int = 0
    removed: int = 0
    changed: int = 0

    @property
    def has_changes(self) -> bool:
        return self.added > 0 or self.removed > 0 or self.changed > 0


@dataclass
class FileChange:
    path: str
    change_type: str  # "added", "removed", "changed"
    properties: list[str] = field(default_factory=list)  # ex: ["mtime", "sha256"]
    raw: str = ""


@dataclass
class CheckResult:
    success: bool
    summary: CheckSummary
    changes: list[FileChange]
    error: str = ""
    duration_seconds: int = 0
    started_at: datetime | None = None
    raw_output: str = ""

    @property
    def baseline_match(self) -> bool:
        """True quando AIDE encontrou ZERO mudancas (sistema intacto)."""
        return self.success and not self.summary.has_changes


# ============================================================
# Profile resolution
# ============================================================


def active_conf_path() -> Path:
    return AIDE_CONF_SYSTEM


def active_db_path() -> Path:
    return AIDE_DB_SYSTEM


def active_db_new_path() -> Path:
    return AIDE_DB_NEW_SYSTEM


# ============================================================
# Sanity checks
# ============================================================


def aide_installed() -> bool:
    return shutil.which("aide") is not None


def baseline_exists() -> bool:
    """Baseline do perfil ATIVO existe?

    LGPD HARDENING: nao tenta stat /var/lib/aide/ (dir e' 0700 — root only).
    Usa cache em STATE_FILE como proxy. Atualizado em init/update via
    `save_state({'baseline_exists': True})`.
    """
    state = load_state()
    if state.get("baseline_exists") is True:
        return True
    # Fallback: tenta stat (funciona se /var/lib/aide ja foi chmodded
    # antes do hardening, ou se rodando como root)
    try:
        return active_db_path().is_file()
    except (OSError, PermissionError):
        return False


def baseline_age_seconds() -> int | None:
    """Idade do baseline em segundos. Usa STATE_FILE timestamp como proxy."""
    state = load_state()
    ts = state.get("baseline_mtime")
    if isinstance(ts, (int, float)):
        return int(time.time() - ts)
    # Fallback: stat direto (precisa permissao)
    db = active_db_path()
    try:
        return int(time.time() - db.stat().st_mtime)
    except (OSError, PermissionError):
        return None


def aide_conf_exists() -> bool:
    """Config do perfil ATIVO existe?"""
    return active_conf_path().is_file()


def format_age(seconds: int | None) -> str:
    if seconds is None:
        return "Nunca"
    if seconds < 60:
        return "agora mesmo"
    minutes = seconds // 60
    if minutes < 60:
        return f"há {minutes} min"
    hours = minutes // 60
    if hours < 24:
        return f"há {hours}h"
    days = hours // 24
    return f"há {days} dia{'s' if days > 1 else ''}"


# ============================================================
# State (cache local)
# ============================================================


def load_state() -> dict:
    # HARDENING: arquivo editavel/corrompivel — garante dict.
    data = load_json(STATE_FILE, {})
    return data if isinstance(data, dict) else {}


def save_state(state: dict) -> None:
    """Salva state em ~/.config/vigia/file-integrity.json com mode 0600.

    LGPD HARDENING: state file contem timestamps de check, contagens de
    diffs. Em sistema multi-user, outros usuarios poderiam inferir
    atividade de baseline checking. Forca 0600 (escrita atomica).
    """
    save_json_0600(STATE_FILE, state)


def get_last_check() -> tuple[datetime | None, CheckSummary | None]:
    state = load_state()
    last = state.get("last_check")
    if not isinstance(last, dict):
        # HARDENING: state e' editavel/corrompivel; last_check pode nao ser
        # dict (string/lista) — sem isso, last.get(...) levantaria AttributeError.
        return None, None
    try:
        ts = datetime.fromisoformat(last.get("timestamp", ""))
    except (ValueError, TypeError):
        ts = None
    summary = CheckSummary(
        total_entries=int(last.get("total_entries", 0)),
        added=int(last.get("added", 0)),
        removed=int(last.get("removed", 0)),
        changed=int(last.get("changed", 0)),
    )
    return ts, summary


def save_last_check(result: CheckResult) -> None:
    state = load_state()
    state["last_check"] = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "total_entries": result.summary.total_entries,
        "added": result.summary.added,
        "removed": result.summary.removed,
        "changed": result.summary.changed,
        "duration_seconds": result.duration_seconds,
    }
    save_state(state)


# ============================================================
# Parser do output de `aide --check`
# ============================================================


SUMMARY_PATTERNS = [
    (r"Total number of entries:\s*(\d+)", "total_entries"),
    (r"Added entries:\s*(\d+)", "added"),
    (r"Removed entries:\s*(\d+)", "removed"),
    (r"Changed entries:\s*(\d+)", "changed"),
]


def parse_check_output(text: str) -> tuple[CheckSummary, list[FileChange]]:
    """Parseia output de `aide --check`. Retorna (summary, changes)."""
    summary = CheckSummary()
    for pattern, attr in SUMMARY_PATTERNS:
        m = re.search(pattern, text)
        if m:
            try:
                setattr(summary, attr, int(m.group(1)))
            except ValueError:
                pass

    changes: list[FileChange] = []

    # As secoes "Added/Removed/Changed entries:" tambem aparecem no Summary
    # (sem separadores ---), entao precisamos exigir os separadores.
    added_block = _extract_section(text, "Added entries:")
    for line in _content_lines(added_block):
        path = _extract_path_from_line(line)
        if path:
            changes.append(FileChange(path=path, change_type="added", raw=line))

    removed_block = _extract_section(text, "Removed entries:")
    for line in _content_lines(removed_block):
        path = _extract_path_from_line(line)
        if path:
            changes.append(FileChange(path=path, change_type="removed", raw=line))

    changed_block = _extract_section(text, "Changed entries:")
    for line in _content_lines(changed_block):
        path = _extract_path_from_line(line)
        if path:
            props = _extract_changed_properties(line)
            changes.append(FileChange(path=path, change_type="changed", properties=props, raw=line))

    return summary, changes


def _extract_section(text: str, header: str) -> str:
    """Extrai uma secao do output do AIDE delimitada por linhas de tracos.

    Formato esperado:

        ----------------------
        <header>
        ----------------------

        <conteudo da secao>

        ----------------------
        ...

    Retorna apenas o <conteudo>, sem o header e sem os separadores.
    Importante: header tambem aparece no Summary (sem tracos), por isso
    exigimos os separadores explicitamente.
    """
    escaped = re.escape(header)
    pattern = re.compile(
        rf"-{{5,}}\s*\n{escaped}\s*\n-{{5,}}\s*\n(.*?)(?=\n-{{5,}}|\nEnd timestamp|\Z)",
        re.DOTALL,
    )
    m = pattern.search(text)
    return m.group(1) if m else ""


def _content_lines(block: str) -> list[str]:
    """Filtra linhas que parecem dados (nao separadores --- nem vazias)."""
    out = []
    for ln in block.splitlines():
        s = ln.strip()
        if not s or s.startswith("---") or s.startswith("===") or s.startswith("###"):
            continue
        out.append(ln)
    return out


_PATH_LINE_RE = re.compile(r"^[fld][^:]*?:\s+(/.*)$")


def _extract_path_from_line(line: str) -> str:
    """As linhas tem formato: 'f++++++++: /path/to/file' ou 'f<flags>: /path'.

    Antes usavamos `line.rsplit(":", 1)[1]` que falhava silenciosamente
    com paths contendo ':' (ex: '/var/foo:bar' virava 'bar'). Agora usa
    regex que casa flags + ': ' + path absoluto, capturando tudo do '/'
    em diante (incluindo ':' no nome).
    """
    m = _PATH_LINE_RE.match(line)
    return m.group(1).strip() if m else ""


_PROP_NAMES = {
    "p": "perms",
    "u": "uid",
    "g": "gid",
    "s": "size",
    "b": "blocks",
    "m": "mtime",
    "n": "links",
    "i": "inode",
    "C": "checksum",
    "S": "size_grow",
    "I": "inode_change",
}


def _extract_changed_properties(line: str) -> list[str]:
    """Da linha 'f   p..  ..  ..  ..  m..  ..  : /path', extrai
    propriedades mudadas (perms, mtime, etc.)."""
    flags_part = line.split(":", 1)[0]
    props: list[str] = []
    for ch in flags_part:
        if ch in _PROP_NAMES and _PROP_NAMES[ch] not in props:
            props.append(_PROP_NAMES[ch])
    return props


# ============================================================
# Operacoes (todas via pkexec — UM dialog)
# ============================================================


def run_init_blocking() -> tuple[bool, str]:
    """`aide --init` + `mv aide.db.new.gz aide.db.gz`. Bloqueante.

    Usa o config + db do AIDE padrão do sistema (/etc/aide.conf).
    """
    if not aide_installed():
        return False, (
            "AIDE não está instalado.\n\n"
            "Instale o AIDE:\n" + install_hint("aide")
        )

    conf = active_conf_path()
    db = active_db_path()
    db_new = active_db_new_path()

    if not conf.is_file():
        return False, f"Arquivo de configuração {conf} não encontrado."

    # rm -f remove orfaos de runs abortados.
    # chmod 755 no diretorio: permite ao UI (user andre) fazer Path.is_file()
    # nos db files. Sem isso, /var/lib/aide/ default 0700 bloqueia ate stat.
    # O conteudo dos arquivos db continua 0600 — so listing/stat e' afetado.
    script = f"""set -e
rm -f {db_new}
aide -c {conf} --init
if [ -f {db_new} ]; then
    mv -f {db_new} {db}
    # NOTA: NAO usamos chmod 755 em /var/lib/aide/ (LGPD: outros users
    # poderiam mapear baseline existence). Status cacheado em STATE_FILE.
else
    echo "ERRO: aide --init nao gerou {db_new}" >&2
    exit 1
fi
"""
    try:
        result = subprocess.run(
            ["pkexec", "bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=1800,
        )
    except subprocess.TimeoutExpired:
        return False, "aide --init demorou mais de 30 minutos. Cancelado."
    except FileNotFoundError:
        return False, "pkexec nao encontrado."

    if result.returncode in (126, 127):
        return False, "Autenticação cancelada."
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        return False, f"aide --init falhou (codigo {result.returncode}):\n\n{stderr[:500]}"

    # LGPD: marca em STATE_FILE que baseline existe (em vez de chmod 755
    # /var/lib/aide para permitir stat — vazaria info para outros users).
    state = load_state()
    state["baseline_exists"] = True
    state["baseline_mtime"] = int(time.time())
    state["baseline_profile"] = state.get("baseline_profile", "")
    save_state(state)

    return True, ""


def run_check_blocking() -> CheckResult:
    """`aide --check`. Bloqueante. Retorna CheckResult."""
    result = CheckResult(success=False, summary=CheckSummary(), changes=[])
    result.started_at = datetime.now()

    if not aide_installed():
        result.error = "AIDE não está instalado."
        return result
    if not baseline_exists():
        result.error = (
            f"Baseline não existe ({active_db_path()}). "
            "Crie primeiro com 'Criar baseline'."
        )
        return result

    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            ["pkexec", "aide", "-c", str(active_conf_path()), "--check"],
            capture_output=True,
            text=True,
            timeout=1800,
        )
    except subprocess.TimeoutExpired:
        result.error = "aide --check demorou mais de 30 minutos. Cancelado."
        return result
    except FileNotFoundError:
        result.error = "pkexec nao encontrado."
        return result

    result.duration_seconds = int(time.monotonic() - t0)

    if proc.returncode in (126, 127):
        result.error = "Autenticação cancelada."
        return result

    # AIDE: 0 = sem mudancas; 1-7 = bitmask de tipos de mudancas detectadas
    if proc.returncode > 7:
        stderr = (proc.stderr or "").strip()
        result.error = f"aide --check falhou (codigo {proc.returncode}):\n\n{stderr[:500]}"
        return result

    text = proc.stdout or ""
    result.raw_output = text
    summary, changes = parse_check_output(text)
    result.summary = summary
    result.changes = changes
    result.success = True

    save_last_check(result)
    return result


def run_update_blocking() -> tuple[bool, str]:
    """`aide --update` + move db.new -> db. Re-baseline mantendo o anterior."""
    if not aide_installed():
        return False, "AIDE não está instalado."
    if not baseline_exists():
        return False, "Sem baseline para atualizar. Use 'Criar baseline'."

    conf = active_conf_path()
    db = active_db_path()
    db_new = active_db_new_path()

    script = f"""set -e
aide -c {conf} --update
if [ -f {db_new} ]; then
    mv -f {db_new} {db}
    # NOTA: NAO usamos chmod 755 em /var/lib/aide/ (LGPD: outros users
    # poderiam mapear baseline existence). Status cacheado em STATE_FILE.
fi
"""
    try:
        result = subprocess.run(
            ["pkexec", "bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=1800,
        )
    except subprocess.TimeoutExpired:
        return False, "aide --update demorou mais de 30 minutos. Cancelado."
    except FileNotFoundError:
        return False, "pkexec nao encontrado."

    if result.returncode in (126, 127):
        return False, "Autenticação cancelada."
    # update tambem usa bitmask (0-7 ok), mas tudo acima e' erro real
    if result.returncode > 7:
        stderr = (result.stderr or "").strip()
        return False, f"aide --update falhou (codigo {result.returncode}):\n\n{stderr[:500]}"

    # LGPD: marca update no STATE_FILE (proxy para baseline_age_seconds)
    state = load_state()
    state["baseline_exists"] = True
    state["baseline_mtime"] = int(time.time())
    save_state(state)

    return True, ""


# ============================================================
# Helpers de UI
# ============================================================


def parse_conf_watched_paths() -> list[str]:
    """Extrai paths monitorados do config do perfil ATIVO.

    Procura por linhas como '/etc f' ou '/usr/bin Norm' (path seguido de
    nome de grupo). Funciona como overview, nao e' completo.
    """
    conf = active_conf_path()
    if not conf.is_file():
        return []
    paths: list[str] = []
    try:
        text = conf.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" in s:
            continue
        # Tipico: "/etc Normal" ou "!/etc/mtab"
        m = re.match(r"(!?/\S+)\s+(\S+)?", s)
        if m:
            paths.append(m.group(1))
    return paths
