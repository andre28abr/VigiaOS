"""Operacoes SELinux invocadas via subprocess.

Read-only (getenforce, getsebool, sestatus, ps -eZ) roda como user.
Operacoes que mudam estado (setenforce, setsebool, edit /etc/selinux/config,
restorecon) requerem root e sao invocadas via pkexec (dialogo polkit).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass

from .descriptions import BOOLEAN_DESCRIPTIONS_PT


# ============================================================================
# Status (mode + policy)
# ============================================================================

def get_mode() -> str:
    """'Enforcing', 'Permissive' ou 'Disabled'."""
    try:
        result = subprocess.run(
            ["getenforce"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return "Unknown"


def get_policy_type() -> str:
    try:
        result = subprocess.run(
            ["sestatus"], capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            if "Loaded policy name:" in line:
                return line.split(":", 1)[1].strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return "Unknown"


def get_policy_version() -> str:
    try:
        result = subprocess.run(
            ["sestatus"], capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            if "Policy version:" in line:
                return line.split(":", 1)[1].strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return "?"


def get_persistent_mode() -> str:
    """Le SELINUX= em /etc/selinux/config. Retorna 'enforcing', 'permissive',
    'disabled' ou 'unknown'. Esse valor e' o que aplica APOS reboot."""
    try:
        with open("/etc/selinux/config") as f:
            for line in f:
                line = line.strip()
                if line.startswith("SELINUX=") and not line.startswith("SELINUXTYPE="):
                    return line.split("=", 1)[1].strip().lower()
    except OSError:
        pass
    return "unknown"


def set_mode_enforcing(enforcing: bool) -> None:
    """Muda modo runtime via pkexec setenforce 0/1."""
    _require_pkexec()
    val = "1" if enforcing else "0"
    _run_pkexec(["setenforce", val], op="setenforce")


def set_persistent_mode(mode: str) -> None:
    """Muda /etc/selinux/config para persistir no boot. mode in
    ('enforcing', 'permissive', 'disabled'). Disabled requer reboot
    para tomar efeito."""
    if mode not in ("enforcing", "permissive", "disabled"):
        raise ValueError(f"Modo invalido: {mode}")
    _require_pkexec()
    # Usa sed via shell para reescrever a linha SELINUX=
    cmd = [
        "pkexec", "sh", "-c",
        f"sed -i 's/^SELINUX=.*/SELINUX={mode}/' /etc/selinux/config"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout).strip()
        if "Request dismissed" in stderr or result.returncode == 126:
            raise RuntimeError("Autenticacao cancelada pelo usuario.")
        raise RuntimeError(f"Falha ao editar /etc/selinux/config: {stderr}")


# ============================================================================
# Booleans
# ============================================================================

@dataclass
class Boolean:
    name: str
    value: bool
    description: str = ""

    @property
    def display_description(self) -> str:
        # Prioridade: dict pt-BR > descricao do semanage > vazio
        custom = BOOLEAN_DESCRIPTIONS_PT.get(self.name)
        if custom:
            return custom
        if self.description:
            return self.description
        return "Sem descricao disponivel."


def list_booleans() -> list[Boolean]:
    """Tenta semanage primeiro (tem descricoes upstream), fallback getsebool."""
    booleans = _try_semanage_booleans()
    if not booleans:
        booleans = _getsebool_booleans()
    return booleans


def _try_semanage_booleans() -> list[Boolean]:
    if shutil.which("semanage") is None:
        return []
    try:
        result = subprocess.run(
            ["semanage", "boolean", "-l"],
            capture_output=True, text=True, timeout=15,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return []
    if result.returncode != 0 or not result.stdout.strip():
        return []

    pattern = re.compile(r"^(\S+)\s+\(\s*(\S+?)\s*,\s*(\S+?)\s*\)\s*(.*)$")
    booleans: list[Boolean] = []
    for line in result.stdout.splitlines():
        line = line.rstrip()
        if not line or line.startswith("SELinux boolean") or "----" in line:
            continue
        match = pattern.match(line)
        if not match:
            continue
        name, current, _default, description = match.groups()
        booleans.append(Boolean(
            name=name,
            value=current.lower() == "on",
            description=description.strip(),
        ))
    return booleans


def _getsebool_booleans() -> list[Boolean]:
    try:
        result = subprocess.run(
            ["getsebool", "-a"],
            capture_output=True, text=True, timeout=10,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return []
    booleans: list[Boolean] = []
    for line in result.stdout.splitlines():
        parts = line.split("-->", 1)
        if len(parts) != 2:
            continue
        booleans.append(Boolean(
            name=parts[0].strip(),
            value=parts[1].strip().lower() == "on",
        ))
    return booleans


def set_boolean(name: str, value: bool, persistent: bool = True) -> None:
    _require_pkexec()
    args = ["setsebool"]
    if persistent:
        args.append("-P")
    args.extend([name, "on" if value else "off"])
    _run_pkexec(args, op=f"setsebool {name}")


# ============================================================================
# AVC Denials + audit2allow
# ============================================================================

@dataclass
class Denial:
    timestamp: str
    comm: str
    pid: str
    op: str            # ex: 'write', 'read'
    name: str          # path/object name
    scontext: str
    tcontext: str
    tclass: str
    permissive: bool
    raw: str           # linha original para passar para audit2allow


def get_recent_denials(since: str = "today") -> list[Denial]:
    """Le AVC denials recentes via 'pkexec ausearch -m AVC -ts <since> --raw'.

    ausearch precisa de root para ler /var/log/audit/audit.log.
    since: 'today', 'this-week', 'recent' (default ultimos 10min), ou data.
    """
    _require_pkexec()
    cmd = ["pkexec", "ausearch", "-m", "AVC", "-ts", since, "--raw"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 1 and "no matches" in (result.stdout + result.stderr).lower():
        return []  # nenhum denial — nao e' erro
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout).strip()
        if "Request dismissed" in stderr or result.returncode == 126:
            raise RuntimeError("Autenticacao cancelada pelo usuario.")
        raise RuntimeError(f"ausearch falhou: {stderr}")
    return _parse_ausearch_avc(result.stdout)


def _parse_ausearch_avc(output: str) -> list[Denial]:
    """Parser simples para linhas 'type=AVC msg=audit(...): avc: denied ...'."""
    denials: list[Denial] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line.startswith("type=AVC"):
            continue
        # Timestamp e id
        ts_match = re.search(r"msg=audit\(([\d.]+):\d+\)", line)
        timestamp = ts_match.group(1) if ts_match else "?"

        # Op em { X }
        op_match = re.search(r"\{\s*(\S+)\s*\}", line)
        op = op_match.group(1) if op_match else "?"

        # Permissive
        perm_match = re.search(r"permissive=(\d)", line)
        permissive = (perm_match.group(1) == "1") if perm_match else False

        fields = dict(re.findall(r'(\w+)="?([^"\s]+)"?', line))
        denials.append(Denial(
            timestamp=timestamp,
            comm=fields.get("comm", "?"),
            pid=fields.get("pid", "?"),
            op=op,
            name=fields.get("name", "?"),
            scontext=fields.get("scontext", "?"),
            tcontext=fields.get("tcontext", "?"),
            tclass=fields.get("tclass", "?"),
            permissive=permissive,
            raw=raw_line,
        ))
    return denials


def audit2allow_suggest(denial_raw: str) -> str:
    """Roda audit2allow com a linha raw via stdin e devolve a sugestao
    de policy module. Usa o binario 'audit2allow' que ja vem com
    policycoreutils-python-utils."""
    if shutil.which("audit2allow") is None:
        return "audit2allow nao instalado. Instale 'policycoreutils-python-utils'."
    try:
        result = subprocess.run(
            ["audit2allow"],
            input=denial_raw,
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return result.stderr.strip() or "(sem sugestao gerada)"
    except subprocess.SubprocessError as e:
        return f"Erro ao rodar audit2allow: {e}"


# ============================================================================
# File contexts (restorecon)
# ============================================================================

def restorecon(path: str, recursive: bool = True, verbose: bool = True) -> str:
    """Restaura contextos SELinux de um path. Retorna output do comando."""
    _require_pkexec()
    args = ["pkexec", "restorecon"]
    if recursive:
        args.append("-R")
    if verbose:
        args.append("-v")
    # '--' separa flags de argumentos posicionais. Sem isso, path tipo
    # '--help' ou '-F' seria interpretado como flag pelo restorecon.
    args.append("--")
    args.append(path)
    result = subprocess.run(args, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout).strip()
        if "Request dismissed" in stderr or result.returncode == 126:
            raise RuntimeError("Autenticacao cancelada pelo usuario.")
        raise RuntimeError(f"restorecon falhou: {stderr}")
    return result.stdout.strip() or "Nenhuma label precisava ser restaurada."


# ============================================================================
# Network ports
# ============================================================================

@dataclass
class PortMapping:
    context: str        # ex: 'http_port_t'
    proto: str          # 'tcp' or 'udp'
    ports: str          # ex: '80, 443, 8443'


def list_ports() -> list[PortMapping]:
    """Le 'semanage port -l'. Funciona como user."""
    if shutil.which("semanage") is None:
        return []
    try:
        result = subprocess.run(
            ["semanage", "port", "-l"],
            capture_output=True, text=True, timeout=15,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return []
    if result.returncode != 0:
        return []
    mappings: list[PortMapping] = []
    # Formato: <context_t>             <proto>      <ports>
    for line in result.stdout.splitlines():
        if not line or line.startswith("SELinux Port Type") or "----" in line:
            continue
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        ctx, proto, ports = parts
        mappings.append(PortMapping(context=ctx, proto=proto, ports=ports.strip()))
    return mappings


# ============================================================================
# Process contexts
# ============================================================================

@dataclass
class ProcessInfo:
    pid: str
    context: str
    user: str
    comm: str


def list_processes(limit: int = 200) -> list[ProcessInfo]:
    """Le 'ps -eZ' para contextos SELinux de processos rodando."""
    try:
        result = subprocess.run(
            ["ps", "-eZ", "-o", "label,pid,user,comm", "--no-headers"],
            capture_output=True, text=True, timeout=10,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return []
    if result.returncode != 0:
        return []
    out: list[ProcessInfo] = []
    for line in result.stdout.splitlines()[:limit]:
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        out.append(ProcessInfo(
            context=parts[0],
            pid=parts[1],
            user=parts[2],
            comm=parts[3],
        ))
    return out


# ============================================================================
# Availability
# ============================================================================

def is_selinux_available() -> bool:
    return (
        shutil.which("getenforce") is not None
        and shutil.which("getsebool") is not None
    )


# ============================================================================
# Internal helpers
# ============================================================================

def _require_pkexec() -> None:
    if shutil.which("pkexec") is None:
        raise RuntimeError("pkexec nao encontrado. Instale 'polkit' via rpm-ostree.")


def _run_pkexec(args: list[str], *, op: str) -> None:
    """Roda 'pkexec <args>' e trata cancelamento de polkit."""
    result = subprocess.run(
        ["pkexec"] + args,
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout).strip()
        if "Request dismissed" in stderr or result.returncode == 126:
            raise RuntimeError("Autenticacao cancelada pelo usuario.")
        raise RuntimeError(f"{op} falhou: {stderr}")
