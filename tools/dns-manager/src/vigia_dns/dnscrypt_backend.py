"""Backend dnscrypt-proxy (modo avancado do DNS Manager v0.2+).

Operacoes:
- dnscrypt_installed() -> bool
- is_active() -> bool (systemctl is-active dnscrypt-proxy)
- get_status() -> DnsCryptStatus
- enable_blocking() -> (ok, err)  [pkexec systemctl enable --now]
- disable_blocking() -> (ok, err) [pkexec systemctl disable --now]
- list_active_servers() -> list[str]
- set_servers(server_names) -> (ok, err) [edita .toml e restart]
- get_blocklist() -> list[str]
- add_blocklist_entry(domain) -> (ok, err)
- remove_blocklist_entry(domain) -> (ok, err)
- get_stats() -> DnsCryptStats

Configuracao em /etc/dnscrypt-proxy/dnscrypt-proxy.toml.
Blocklist em /etc/dnscrypt-proxy/blacklist.txt (formato: 1 dominio/linha).
Backup atomico: .vigia-backup do .toml antes de cada write.

TOML parsing: Python 3.11+ tem `tomllib` no stdlib (read-only). Para
write, regravamos preservando estrutura via approach line-based
(detecta key, substitui valor, mantem comments).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:
    tomllib = None  # type: ignore


CONFIG_PATH = Path("/etc/dnscrypt-proxy/dnscrypt-proxy.toml")
BACKUP_PATH = Path("/etc/dnscrypt-proxy/dnscrypt-proxy.toml.vigia-backup")
BLOCKLIST_PATH = Path("/etc/dnscrypt-proxy/blacklist.txt")
QUERY_LOG_PATH = Path("/var/log/dnscrypt-proxy/query.log")

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
    config_writable_via_pkexec: bool = True
    listen_address: str = "127.0.0.1:53"
    server_names: list[str] = field(default_factory=list)
    require_dnssec: bool = False
    require_nofilter: bool = False
    require_nolog: bool = False
    blocklist_size: int = 0
    blocklist_enabled: bool = False
    query_log_enabled: bool = False


@dataclass
class DnsCryptStats:
    """Estatisticas extraidas de query.log (se habilitado)."""
    total_queries: int = 0
    blocked_count: int = 0
    cached_count: int = 0
    top_domains: list[tuple[str, int]] = field(default_factory=list)
    log_available: bool = False
    log_path: str = ""
    last_24h: bool = True               # janela analisada


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
        # Output: "2.1.5" ou multi-line — pega primeira linha que parece versao
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
# Config parsing (TOML read-only via tomllib + line-based write)
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
    except (OSError, PermissionError, Exception):
        # tomllib.TOMLDecodeError so existe em 3.11+, usa Exception generico
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
        # listen_addresses pode ser ["127.0.0.1:53"] ou similar
        listen = data.get("listen_addresses", [])
        if listen:
            st.listen_address = listen[0]

        servers = data.get("server_names", [])
        if isinstance(servers, list):
            st.server_names = [str(s) for s in servers]

        st.require_dnssec = bool(data.get("require_dnssec", False))
        st.require_nofilter = bool(data.get("require_nofilter", False))
        st.require_nolog = bool(data.get("require_nolog", False))

        # Blocklist config: [blocked_names] block_file = "..."
        blocked = data.get("blocked_names", {})
        block_file = blocked.get("block_file") if isinstance(blocked, dict) else None
        st.blocklist_enabled = bool(block_file)

        # Query log: [query_log] file = "..."
        qlog = data.get("query_log", {})
        qlog_file = qlog.get("file") if isinstance(qlog, dict) else None
        st.query_log_enabled = bool(qlog_file)

    # Conta entradas da blocklist (mesmo se nao configurada na .toml,
    # o user pode ter o arquivo do Vigia)
    if BLOCKLIST_PATH.exists():
        try:
            with open(BLOCKLIST_PATH, "r", encoding="utf-8") as f:
                st.blocklist_size = sum(
                    1 for line in f
                    if line.strip() and not line.strip().startswith("#")
                )
        except (OSError, PermissionError):
            pass

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
    in_section = False  # detecta se entrou numa section [xyz]

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
        # Adiciona ao topo (antes de qualquer [section])
        insert_idx = 0
        for i, line in enumerate(out):
            if line.strip().startswith("["):
                insert_idx = i
                break
            insert_idx = i + 1
        out.insert(insert_idx, f"{key} = {new_value}\n")

    return out


def _update_toml_section_key(
    lines: list[str], section: str, key: str, new_value: str
) -> list[str]:
    """Substitui 'key = ...' dentro de [section]. Adiciona se nao existir."""
    out: list[str] = []
    in_section = False
    section_found = False
    key_replaced = False
    pattern = re.compile(rf"^(\s*){re.escape(key)}\s*=")
    section_header = f"[{section}]"

    for line in lines:
        stripped = line.strip()
        if stripped == section_header:
            in_section = True
            section_found = True
            out.append(line)
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            if in_section and not key_replaced:
                # Saindo da section sem encontrar a key — adiciona antes
                out.append(f"{key} = {new_value}\n")
                key_replaced = True
            in_section = False
            out.append(line)
            continue

        if in_section and pattern.match(line):
            indent_match = pattern.match(line)
            indent = indent_match.group(1) if indent_match else ""
            out.append(f"{indent}{key} = {new_value}\n")
            key_replaced = True
        else:
            out.append(line)

    if in_section and not key_replaced:
        out.append(f"{key} = {new_value}\n")
        key_replaced = True

    if not section_found:
        # Cria section no fim
        out.append(f"\n[{section}]\n")
        out.append(f"{key} = {new_value}\n")

    return out


def _atomic_write_config_via_pkexec(new_content: str) -> tuple[bool, str]:
    """Escreve novo config.toml via pkexec.

    Faz backup (.vigia-backup) primeiro se nao existe. Escreve atomico
    via temp file + mv.
    """
    if shutil.which("pkexec") is None:
        return False, "pkexec nao encontrado."

    # Heredoc UUID-delimited para evitar colisao
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

# Restart service se ativo
if systemctl is-active --quiet {SERVICE_NAME}; then
    systemctl restart {SERVICE_NAME}
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
    """`pkexec systemctl enable --now dnscrypt-proxy`.

    Antes de ativar, sugere parar systemd-resolved (mas nao para —
    deixa user decidir explicitamente via migration.py).
    """
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

    # Validacao: server names apenas chars seguros
    safe = []
    for name in server_names:
        if not re.match(r"^[a-zA-Z0-9._\-]+$", name):
            return False, f"Nome de server invalido: {name!r}"
        safe.append(name)

    lines = _read_config_lines()
    if not lines:
        return False, "Falha ao ler config (sem permissao?)"

    # Formato TOML array: ["server1", "server2"]
    array_repr = "[" + ", ".join(f"'{s}'" for s in safe) + "]"
    new_lines = _update_toml_key(lines, "server_names", array_repr)
    new_content = "".join(new_lines)

    return _atomic_write_config_via_pkexec(new_content)


# ============================================================
# Blocklist management
# ============================================================


def get_blocklist() -> list[str]:
    """Le blocklist atual (deduplica + skip lines vazias/comentadas)."""
    if not BLOCKLIST_PATH.exists():
        return []
    try:
        domains: list[str] = []
        seen: set[str] = set()
        with open(BLOCKLIST_PATH, "r", encoding="utf-8") as f:
            for line in f:
                d = line.strip()
                if not d or d.startswith("#"):
                    continue
                if d in seen:
                    continue
                seen.add(d)
                domains.append(d)
        return domains
    except (OSError, PermissionError):
        return []


def _validate_domain(domain: str) -> tuple[bool, str]:
    """Valida que `domain` parece dominio razoavel.

    Aceita: example.com, sub.example.com, *.example.com (wildcard).
    Rejeita: chars de shell, espacos, paths.
    """
    if not domain or len(domain) > 253:
        return False, "Dominio vazio ou muito longo."
    if not re.match(r"^[a-zA-Z0-9.\-*]+$", domain):
        return False, "Dominio contem caracteres invalidos."
    if domain.startswith(".") or domain.endswith("."):
        return False, "Dominio nao pode comecar ou terminar com '.'"
    if ".." in domain:
        return False, "'.' duplicado no dominio."
    return True, ""


def add_blocklist_entry(domain: str) -> tuple[bool, str]:
    """Adiciona dominio a blocklist (idempotente — nao duplica)."""
    ok, err = _validate_domain(domain)
    if not ok:
        return False, err

    existing = get_blocklist()
    if domain in existing:
        return True, "ja presente"

    new_list = existing + [domain]
    return _write_blocklist_via_pkexec(new_list)


def remove_blocklist_entry(domain: str) -> tuple[bool, str]:
    """Remove dominio da blocklist."""
    existing = get_blocklist()
    if domain not in existing:
        return True, "nao presente"

    new_list = [d for d in existing if d != domain]
    return _write_blocklist_via_pkexec(new_list)


def _write_blocklist_via_pkexec(domains: list[str]) -> tuple[bool, str]:
    """Escreve nova blocklist via pkexec."""
    if shutil.which("pkexec") is None:
        return False, "pkexec nao encontrado."

    import uuid
    delim = f"VIGIABL_{uuid.uuid4().hex}"
    content = "\n".join(sorted(set(domains))) + "\n"

    script = f"""set -e
mkdir -p {BLOCKLIST_PATH.parent}
TMPFILE=$(mktemp)
cat > "$TMPFILE" << '{delim}'
{content}{delim}
chmod 0644 "$TMPFILE"
chown root:root "$TMPFILE"
mv "$TMPFILE" {BLOCKLIST_PATH}

# Garante que config aponta pra blocklist (idempotente)
# Se ja apontava, nao mexe; se nao apontava, adiciona section.
# Por simplicidade, assumimos que set_blocklist_in_config sera chamado
# separadamente — aqui so escreve o arquivo.
"""
    rc, _, err = _run(["pkexec", "bash", "-c", script], timeout=15)
    if rc in (126, 127):
        return False, "Autenticacao cancelada."
    if rc != 0:
        return False, (err.strip() or "Falha ao escrever blocklist.")[:500]
    return True, ""


def enable_blocklist_in_config() -> tuple[bool, str]:
    """Adiciona [blocked_names] block_file = ... no .toml + restart."""
    lines = _read_config_lines()
    if not lines:
        return False, "Falha ao ler config."

    new_lines = _update_toml_section_key(
        lines, "blocked_names", "block_file", f"'{BLOCKLIST_PATH}'"
    )
    new_content = "".join(new_lines)
    return _atomic_write_config_via_pkexec(new_content)


def import_blocklist_from_url(url: str, append: bool = True) -> tuple[bool, int, str]:
    """Baixa lista de dominios de uma URL HTTP/HTTPS via curl.

    Formato esperado: 1 dominio por linha (comentarios com # OK).
    """
    if not re.match(r"^https?://[a-zA-Z0-9._\-/?=&#:%]+$", url):
        return False, 0, "URL invalida."

    if shutil.which("curl") is None:
        return False, 0, "curl nao encontrado."

    rc, out, err = _run(
        ["curl", "-fsSL", "--max-time", "30", url],
        timeout=35,
    )
    if rc != 0 or not out:
        return False, 0, (err.strip() or "Falha no download.")[:300]

    # Parseia: 1 dominio por linha, ignora comentarios
    new_domains: list[str] = []
    seen: set[str] = set()
    for raw in out.splitlines():
        # Suporta formato hosts (0.0.0.0 domain.com) e formato simples
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        domain = parts[-1] if len(parts) >= 2 else parts[0]
        if not domain or domain in seen:
            continue
        ok, _ = _validate_domain(domain)
        if not ok:
            continue
        seen.add(domain)
        new_domains.append(domain)

    if not new_domains:
        return False, 0, "Nenhum dominio valido na URL."

    if append:
        existing = set(get_blocklist())
        final = existing | set(new_domains)
        ok_w, err_w = _write_blocklist_via_pkexec(sorted(final))
        added = len(set(new_domains) - existing)
    else:
        ok_w, err_w = _write_blocklist_via_pkexec(new_domains)
        added = len(new_domains)

    if not ok_w:
        return False, 0, err_w

    return True, added, ""


# ============================================================
# Stats (parsing query.log)
# ============================================================


def get_stats() -> DnsCryptStats:
    """Le query.log e agrega stats das ultimas 24h."""
    stats = DnsCryptStats(log_path=str(QUERY_LOG_PATH))

    if not QUERY_LOG_PATH.exists():
        return stats

    stats.log_available = True

    # Janela: ultimas 24h
    cutoff = time.time() - 86400

    # Counters
    domain_counts: dict[str, int] = {}
    try:
        with open(QUERY_LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                # Formato dnscrypt-proxy query.log:
                # [timestamp] client_ip qname qtype status server
                # status: PASS, FORWARD, REJECT, etc.
                parts = line.split()
                if len(parts) < 5:
                    continue

                # Timestamp pode estar entre [] no inicio
                ts_str = parts[0].lstrip("[").rstrip("]")
                try:
                    # dnscrypt-proxy default timestamp: ltsv ou texto YYYY-MM-DDTHH:MM:SS
                    if "T" in ts_str:
                        # ISO format
                        import datetime
                        dt = datetime.datetime.fromisoformat(ts_str)
                        ts = dt.timestamp()
                    else:
                        # Epoch
                        ts = float(ts_str)
                    if ts < cutoff:
                        continue
                except (ValueError, IndexError):
                    pass  # ignora linhas mal formadas

                stats.total_queries += 1

                # Status no penultimo ou ultimo field tipicamente
                status = ""
                for p in parts:
                    if p.upper() in ("PASS", "FORWARD", "REJECT", "DROP", "SYNTH"):
                        status = p.upper()
                        break

                if status in ("REJECT", "DROP"):
                    stats.blocked_count += 1
                elif status == "SYNTH":
                    stats.cached_count += 1

                # Conta dominio (qname tipicamente parts[2])
                if len(parts) >= 3:
                    domain = parts[2].lower()
                    if domain and len(domain) < 100:  # sanity
                        domain_counts[domain] = domain_counts.get(domain, 0) + 1
    except (OSError, PermissionError):
        return stats

    # Top 10 dominios
    sorted_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)
    stats.top_domains = sorted_domains[:10]

    return stats


# ============================================================
# Helpers de migracao (chamados pelo migration.py)
# ============================================================


def has_backup() -> bool:
    """Existe backup do .toml original?"""
    return BACKUP_PATH.exists()


def restore_from_backup_blocking() -> tuple[bool, str]:
    """Restaura .toml original a partir do .vigia-backup."""
    if not BACKUP_PATH.exists():
        return False, "Sem backup disponivel."
    if shutil.which("pkexec") is None:
        return False, "pkexec nao encontrado."

    script = f"""set -e
cp -a {BACKUP_PATH} {CONFIG_PATH}
if systemctl is-active --quiet {SERVICE_NAME}; then
    systemctl restart {SERVICE_NAME}
fi
"""
    rc, _, err = _run(["pkexec", "bash", "-c", script], timeout=15)
    if rc in (126, 127):
        return False, "Autenticacao cancelada."
    if rc != 0:
        return False, (err.strip() or "Falha ao restaurar backup.")[:500]
    return True, ""
