"""Backend WireGuard.

Operacoes:
- wireguard_installed() -> bool
- list_profiles_elevated() -> list[VpnProfile] (via pkexec, le /etc/wireguard/)
- list_active_interfaces() -> list[str]
- get_interface_status_elevated(iface) -> IfaceStatus
- connect_blocking(profile) -> (success, error_message)
- disconnect_blocking(profile) -> (success, error_message)

Quase tudo precisa root: /etc/wireguard/ tipicamente tem mode 0700.
Para evitar spam de polkit, agrupamos operacoes em scripts bash unicos
quando possivel.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


WIREGUARD_CONFIG_DIR = Path("/etc/wireguard")


@dataclass
class VpnProfile:
    name: str               # nome do perfil (sem .conf)
    path: str               # /etc/wireguard/<name>.conf
    address: str = ""       # IP do peer (extraido do conf)
    dns: str = ""           # DNS configurado
    endpoint: str = ""      # endpoint do servidor


@dataclass
class IfaceStatus:
    iface: str
    public_key: str = ""
    listening_port: str = ""
    peers: list[dict] = field(default_factory=list)
    rx_bytes: int = 0
    tx_bytes: int = 0


# ============================================================
# Sanity
# ============================================================


def wireguard_installed() -> bool:
    return shutil.which("wg") is not None and shutil.which("wg-quick") is not None


def _run(cmd: list[str], timeout: int = 15) -> tuple[int, str, str]:
    """Roda comando, retorna (rc, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 1, "", ""


# ============================================================
# Listing
# ============================================================


def list_active_interfaces() -> list[str]:
    """Interfaces WireGuard ativas (sem pkexec — `wg show interfaces` e' user-readable)."""
    if not wireguard_installed():
        return []
    rc, out, _ = _run(["wg", "show", "interfaces"])
    if rc != 0:
        return []
    return out.strip().split()


def list_profiles_elevated() -> tuple[list[VpnProfile], str]:
    """Lista perfis em /etc/wireguard/*.conf via pkexec.

    Retorna (profiles, error_message). Se autenticacao cancelada,
    error_message != ''.
    """
    if not wireguard_installed():
        return [], "WireGuard nao instalado (pacote wireguard-tools)."

    # Script: lista os .conf + cat de cada um. Output formato:
    # ===VIGIA_PROFILE===<name>
    # <conteudo>
    # ===VIGIA_PROFILE_END===
    script = """set +e
shopt -s nullglob 2>/dev/null
for f in /etc/wireguard/*.conf; do
    [ -f "$f" ] || continue
    name=$(basename "$f" .conf)
    echo "===VIGIA_PROFILE===$name"
    cat "$f"
    echo "===VIGIA_PROFILE_END==="
done
"""
    rc, out, err = _run(["pkexec", "bash", "-c", script], timeout=30)

    if rc in (126, 127):
        return [], "Autenticacao cancelada."
    if rc != 0 and not out:
        return [], (err.strip() or "Falha ao listar perfis.")

    return _parse_profiles_output(out), ""


def _parse_profiles_output(text: str) -> list[VpnProfile]:
    """Parseia output do script list_profiles_elevated."""
    profiles: list[VpnProfile] = []
    current_name: str | None = None
    current_content: list[str] = []

    for line in text.splitlines():
        if line.startswith("===VIGIA_PROFILE===") and not line.endswith("_END==="):
            current_name = line[len("===VIGIA_PROFILE==="):].strip()
            current_content = []
        elif line.startswith("===VIGIA_PROFILE_END==="):
            if current_name:
                profiles.append(_parse_single_conf(current_name, current_content))
            current_name = None
            current_content = []
        elif current_name is not None:
            current_content.append(line)

    return profiles


def _parse_single_conf(name: str, lines: list[str]) -> VpnProfile:
    """Extrai campos basicos de um arquivo .conf do WireGuard."""
    address = ""
    dns = ""
    endpoint = ""
    for raw in lines:
        s = raw.strip()
        if s.startswith("#") or "=" not in s:
            continue
        key, _, value = s.partition("=")
        key = key.strip().lower()
        value = value.strip()
        if key == "address":
            address = value
        elif key == "dns":
            dns = value
        elif key == "endpoint":
            endpoint = value

    return VpnProfile(
        name=name,
        path=str(WIREGUARD_CONFIG_DIR / f"{name}.conf"),
        address=address,
        dns=dns,
        endpoint=endpoint,
    )


# ============================================================
# Status de uma interface
# ============================================================


def get_interface_status_elevated(iface: str) -> tuple[IfaceStatus | None, str]:
    """`wg show <iface>` parseado em IfaceStatus.

    Sem pkexec: alguns campos (private keys) sao mascarados. Para info
    completa, este metodo usa pkexec.
    """
    if not wireguard_installed():
        return None, "WireGuard nao instalado."

    rc, out, err = _run(["pkexec", "wg", "show", iface], timeout=10)
    if rc in (126, 127):
        return None, "Autenticacao cancelada."
    if rc != 0:
        return None, err.strip() or f"Falha ao consultar {iface}."

    return _parse_wg_show(iface, out), ""


def _parse_wg_show(iface: str, text: str) -> IfaceStatus:
    """Parseia output legivel do `wg show <iface>`."""
    status = IfaceStatus(iface=iface)
    current_peer: dict | None = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        # interface section
        if line.startswith("interface:"):
            current_peer = None
            continue

        # peer section
        if line.startswith("peer:"):
            if current_peer is not None:
                status.peers.append(current_peer)
            current_peer = {"public_key": line.split(":", 1)[1].strip()}
            continue

        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip().lower()
            val = val.strip()
            if current_peer is None:
                if key == "public key":
                    status.public_key = val
                elif key == "listening port":
                    status.listening_port = val
            else:
                if key == "transfer":
                    m = re.match(r"([\d.]+\s*\w+)\s+received,\s+([\d.]+\s*\w+)\s+sent", val)
                    if m:
                        current_peer["rx"] = m.group(1)
                        current_peer["tx"] = m.group(2)
                elif key == "endpoint":
                    current_peer["endpoint"] = val
                elif key == "allowed ips":
                    current_peer["allowed_ips"] = val
                elif key == "latest handshake":
                    current_peer["latest_handshake"] = val

    if current_peer is not None:
        status.peers.append(current_peer)

    return status


# ============================================================
# Connect / Disconnect
# ============================================================


def connect_blocking(profile_name: str) -> tuple[bool, str]:
    """`pkexec wg-quick up <profile>`."""
    if not wireguard_installed():
        return False, "WireGuard nao instalado."

    # Sanitize: nome do profile so com chars validos
    if not re.match(r"^[a-zA-Z0-9._-]+$", profile_name):
        return False, "Nome de perfil invalido."

    rc, out, err = _run(["pkexec", "wg-quick", "up", profile_name], timeout=30)
    if rc in (126, 127):
        return False, "Autenticacao cancelada."
    if rc != 0:
        msg = (err or out).strip()
        return False, f"Falha ao conectar:\n\n{msg[:500]}"
    return True, ""


def disconnect_blocking(profile_name: str) -> tuple[bool, str]:
    """`pkexec wg-quick down <profile>`."""
    if not wireguard_installed():
        return False, "WireGuard nao instalado."

    if not re.match(r"^[a-zA-Z0-9._-]+$", profile_name):
        return False, "Nome de perfil invalido."

    rc, out, err = _run(["pkexec", "wg-quick", "down", profile_name], timeout=30)
    if rc in (126, 127):
        return False, "Autenticacao cancelada."
    if rc != 0:
        msg = (err or out).strip()
        return False, f"Falha ao desconectar:\n\n{msg[:500]}"
    return True, ""


# ============================================================
# Import (instala um arquivo de config em /etc/wireguard/)
# ============================================================


def import_profile_blocking(name: str, conf_content: str) -> tuple[bool, str]:
    """Instala `conf_content` como /etc/wireguard/<name>.conf via pkexec.

    Faz chmod 600 e chown root:root no resultado (recomendacao WireGuard).
    """
    if not wireguard_installed():
        return False, "WireGuard nao instalado."

    if not re.match(r"^[a-zA-Z0-9._-]+$", name):
        return False, "Nome de perfil invalido (use apenas a-z, 0-9, ._-)."

    if not conf_content.strip():
        return False, "Conteudo da configuracao vazio."

    # Heredoc com delim UUID para evitar colisao com conteudo
    import uuid
    delim = f"VIGIAVPN_{uuid.uuid4().hex}"
    script = f"""set -e
mkdir -p /etc/wireguard
chmod 700 /etc/wireguard
cat > /etc/wireguard/{name}.conf << '{delim}'
{conf_content}
{delim}
chmod 600 /etc/wireguard/{name}.conf
chown root:root /etc/wireguard/{name}.conf
"""
    rc, out, err = _run(["pkexec", "bash", "-c", script], timeout=30)
    if rc in (126, 127):
        return False, "Autenticacao cancelada."
    if rc != 0:
        msg = (err or out).strip()
        return False, f"Falha ao importar:\n\n{msg[:500]}"
    return True, ""
