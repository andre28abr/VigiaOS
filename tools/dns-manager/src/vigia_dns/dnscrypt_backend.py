"""Backend dnscrypt-proxy — v0.4.0 (enxugado).

Removido na v0.4.0: get_blocklist, add/remove_blocklist_entry,
import_blocklist_from_url, enable_blocklist_in_config,
enable/disable_query_log_in_config, get_stats, _validate_domain.

Motivacao: ad-blocking e telemetria de queries sao feitos melhor por
extensoes de navegador (uBlock Origin, Privacy Badger) que ficam no
Vigia Tool Installer. DNS Manager foca no que faz bem: DNS encriptado.

Operacoes mantidas:
- dnscrypt_installed() -> bool
- is_active() / is_enabled() -> bool
- get_status() -> DnsCryptStatus
- get_version() -> str
- set_servers_blocking(server_names) -> (ok, err) [edita .toml + restart]
- enable_blocking() / disable_blocking() -> (ok, err) [pkexec systemctl]
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:
    tomllib = None  # type: ignore


CONFIG_PATH = Path("/etc/dnscrypt-proxy/dnscrypt-proxy.toml")
BACKUP_PATH = Path("/etc/dnscrypt-proxy/dnscrypt-proxy.toml.vigia-backup")

SERVICE_NAME = "dnscrypt-proxy"


# ============================================================
# Dataclasses
# ============================================================


@dataclass
class DnsCryptStatus:
    installed: bool = False
    active: bool = False               # service running
    enabled: bool = False              # systemctl enabled (boot)
    version: str = ""
    config_exists: bool = False
    listen_address: str = "127.0.0.1:53"
    server_names: list[str] = field(default_factory=list)
    require_dnssec: bool = False
    require_nofilter: bool = False
    require_nolog: bool = False


# ============================================================
# Sanity
# ============================================================


def dnscrypt_installed() -> bool:
    """Checa se o binario dnscrypt-proxy existe."""
    return shutil.which("dnscrypt-proxy") is not None


def is_active() -> bool:
    """systemctl is-active dnscrypt-proxy (sem pkexec — user pode)."""
    if shutil.which("systemctl") is None:
        return False
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "--quiet", SERVICE_NAME],
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def is_enabled() -> bool:
    """systemctl is-enabled dnscrypt-proxy."""
    if shutil.which("systemctl") is None:
        return False
    try:
        result = subprocess.run(
            ["systemctl", "is-enabled", "--quiet", SERVICE_NAME],
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_version() -> str:
    """`dnscrypt-proxy -version` retorna versao."""
    if not dnscrypt_installed():
        return ""
    try:
        result = subprocess.run(
            ["dnscrypt-proxy", "-version"],
            capture_output=True, text=True, timeout=5,
        )
        for line in (result.stdout or "").splitlines():
            line = line.strip()
            if re.match(r"^\d+\.\d+(\.\d+)?", line):
                return line
        return (result.stdout or "").strip().split("\n")[0]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def _run(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 1, "", ""


# ============================================================
# Config parsing
# ============================================================


def _read_config_parsed() -> dict:
    """Le config.toml via tomllib. Retorna dict ou {} se erro."""
    if not CONFIG_PATH.exists():
        return {}
    if tomllib is None:
        return {}
    try:
        with open(CONFIG_PATH, "rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        # Erro de leitura/parse conhecido => trata como "sem config".
        # (Erros inesperados propagam de proposito — nao mascarar bug.)
        return {}


def get_status() -> DnsCryptStatus:
    """Coleta status completo."""
    st = DnsCryptStatus()
    st.installed = dnscrypt_installed()
    if not st.installed:
        return st

    st.active = is_active()
    st.enabled = is_enabled()
    st.version = get_version()
    st.config_exists = CONFIG_PATH.exists()

    if st.config_exists:
        data = _read_config_parsed()
        listen = data.get("listen_addresses", [])
        if listen:
            st.listen_address = listen[0]

        servers = data.get("server_names", [])
        if isinstance(servers, list):
            st.server_names = [str(s) for s in servers]

        st.require_dnssec = bool(data.get("require_dnssec", False))
        st.require_nofilter = bool(data.get("require_nofilter", False))
        st.require_nolog = bool(data.get("require_nolog", False))

    return st


# ============================================================
# Config write (line-based, preserva comments)
# ============================================================


def _read_config_lines() -> list[str]:
    """Le config.toml como lista de linhas. Retorna [] se nao puder."""
    if not CONFIG_PATH.exists():
        return []
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return f.readlines()
    except (OSError, PermissionError):
        return []


def _update_toml_key(lines: list[str], key: str, new_value: str) -> list[str]:
    """Substitui linha 'key = ...' por 'key = <new_value>'.

    Procura no scope global (sem section). Se nao achar, adiciona ao fim.
    Preserva indentacao e comments.
    """
    pattern = re.compile(rf"^(\s*){re.escape(key)}\s*=", re.MULTILINE)
    out: list[str] = []
    replaced = False
    in_section = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_section = True

        if not in_section and pattern.match(line):
            indent_match = pattern.match(line)
            indent = indent_match.group(1) if indent_match else ""
            out.append(f"{indent}{key} = {new_value}\n")
            replaced = True
        else:
            out.append(line)

    if not replaced:
        insert_idx = 0
        for i, line in enumerate(out):
            if line.strip().startswith("["):
                insert_idx = i
                break
            insert_idx = i + 1
        out.insert(insert_idx, f"{key} = {new_value}\n")

    return out


def _atomic_write_config_via_pkexec(new_content: str) -> tuple[bool, str]:
    """Escreve novo config.toml via pkexec.

    Backup (.vigia-backup) primeiro se nao existe. Atomico via temp + mv.
    """
    if shutil.which("pkexec") is None:
        return False, "pkexec nao encontrado."

    import uuid
    delim = f"VIGIADNS_{uuid.uuid4().hex}"

    script = f"""set -e
# Backup do arquivo original (so primeira vez — preserva o vanilla)
if [ -f {CONFIG_PATH} ] && [ ! -f {BACKUP_PATH} ]; then
    cp -a {CONFIG_PATH} {BACKUP_PATH}
    chmod 0600 {BACKUP_PATH}
fi

# Escreve atomico em temp + mv (heredoc)
TMPFILE=$(mktemp)
cat > "$TMPFILE" << '{delim}'
{new_content}
{delim}
chmod 0644 "$TMPFILE"
chown root:root "$TMPFILE"
mv "$TMPFILE" {CONFIG_PATH}

# v0.4.1: garante cache dir existe (elimina warning no journal).
# Detecta user/group do unit file dinamicamente; root como fallback.
DCS_USER=$(systemctl show {SERVICE_NAME} -p User --value 2>/dev/null)
DCS_GROUP=$(systemctl show {SERVICE_NAME} -p Group --value 2>/dev/null)
mkdir -p /var/cache/dnscrypt-proxy
if [ -n "$DCS_USER" ] && id "$DCS_USER" >/dev/null 2>&1; then
    chown "${{DCS_USER}}:${{DCS_GROUP:-$DCS_USER}}" /var/cache/dnscrypt-proxy 2>/dev/null || true
fi
chmod 0750 /var/cache/dnscrypt-proxy

# Restart service se ativo + wait
if systemctl is-active --quiet {SERVICE_NAME}; then
    systemctl restart {SERVICE_NAME}
    for i in 1 2 3 4 5 6; do
        if systemctl is-active --quiet {SERVICE_NAME}; then
            break
        fi
        sleep 0.5
    done
fi
"""
    rc, _, err = _run(["pkexec", "bash", "-c", script], timeout=30)
    if rc in (126, 127):
        return False, "Autenticacao cancelada."
    if rc != 0:
        return False, (err.strip() or "Falha ao escrever config.")[:500]
    return True, ""


# ============================================================
# Service control
# ============================================================


def enable_blocking() -> tuple[bool, str]:
    """`pkexec systemctl enable --now dnscrypt-proxy`."""
    if not dnscrypt_installed():
        return False, "dnscrypt-proxy nao instalado."
    if shutil.which("pkexec") is None:
        return False, "pkexec nao encontrado."

    rc, _, err = _run(
        ["pkexec", "systemctl", "enable", "--now", SERVICE_NAME],
        timeout=20,
    )
    if rc in (126, 127):
        return False, "Autenticacao cancelada."
    if rc != 0:
        return False, (err.strip() or "Falha ao ativar service.")[:500]
    return True, ""


def disable_blocking() -> tuple[bool, str]:
    """`pkexec systemctl disable --now dnscrypt-proxy`."""
    if not dnscrypt_installed():
        return False, "dnscrypt-proxy nao instalado."
    if shutil.which("pkexec") is None:
        return False, "pkexec nao encontrado."

    rc, _, err = _run(
        ["pkexec", "systemctl", "disable", "--now", SERVICE_NAME],
        timeout=20,
    )
    if rc in (126, 127):
        return False, "Autenticacao cancelada."
    if rc != 0:
        return False, (err.strip() or "Falha ao desativar service.")[:500]
    return True, ""


# ============================================================
# Server selection
# ============================================================


def set_servers_blocking(server_names: list[str]) -> tuple[bool, str]:
    """Atualiza server_names no .toml + reload do service."""
    if not CONFIG_PATH.exists():
        return False, f"Config nao existe: {CONFIG_PATH}"

    # Validacao: apenas chars seguros (anti-injection)
    safe = []
    for name in server_names:
        if not re.match(r"^[a-zA-Z0-9._\-]+$", name):
            return False, f"Nome de server invalido: {name!r}"
        safe.append(name)

    lines = _read_config_lines()
    if not lines:
        return False, "Falha ao ler config (sem permissao?)"

    array_repr = "[" + ", ".join(f"'{s}'" for s in safe) + "]"
    new_lines = _update_toml_key(lines, "server_names", array_repr)
    new_content = "".join(new_lines)

    return _atomic_write_config_via_pkexec(new_content)
