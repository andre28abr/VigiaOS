"""Backend systemd-resolved.

- Status via `resolvectl status` (parseado em ResolvedStatus)
- Set global DNS editando /etc/systemd/resolved.conf (DNS=, DNSOverTLS=, ...)
- Set per-interface DNS via `resolvectl dns <iface> <ip>` (runtime, nao persiste)
- Flush cache via `resolvectl flush-caches`
"""

from __future__ import annotations

import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path


RESOLVED_CONF = Path("/etc/systemd/resolved.conf")


@dataclass
class InterfaceDns:
    name: str                            # ex: "wlp2s0"
    dns_servers: list[str] = field(default_factory=list)
    dns_over_tls: str = ""               # "yes" / "no" / "opportunistic"
    domains: list[str] = field(default_factory=list)


@dataclass
class ResolvedStatus:
    available: bool = False              # systemd-resolved instalado E ativo
    active: bool = False                 # service status
    global_dns: list[str] = field(default_factory=list)
    global_dot: str = ""
    fallback_dns: list[str] = field(default_factory=list)
    interfaces: list[InterfaceDns] = field(default_factory=list)
    current_dns: list[str] = field(default_factory=list)  # efetivo (resolvectl status)
    raw: str = ""


# ============================================================
# Sanity
# ============================================================


def resolvectl_available() -> bool:
    return shutil.which("resolvectl") is not None


def resolved_active() -> bool:
    """systemd-resolved esta ativo (running)?"""
    try:
        rc = subprocess.run(
            ["systemctl", "is-active", "--quiet", "systemd-resolved"],
            timeout=5,
        ).returncode
        return rc == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _run(cmd: list[str], timeout: int = 10) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 1, "", ""


# ============================================================
# Status (parsing resolvectl status)
# ============================================================


def get_status() -> ResolvedStatus:
    """Coleta estado de DNS via `resolvectl status`. Nao requer pkexec."""
    st = ResolvedStatus()
    if not resolvectl_available():
        return st

    st.available = True
    st.active = resolved_active()

    rc, out, _ = _run(["resolvectl", "status"], timeout=10)
    if rc != 0:
        return st

    st.raw = out
    _parse_resolvectl_status(st, out)
    return st


def _parse_resolvectl_status(st: ResolvedStatus, text: str) -> None:
    """Parser do output do `resolvectl status`.

    Output tipico:
        Global
           Protocols: -LLMNR -mDNS +DNSOverTLS DNSSEC=no/unsupported
        resolv.conf mode: stub
        Current DNS Server: 1.1.1.1
            DNS Servers: 1.1.1.1 1.0.0.1
           Fallback DNS Servers: ...

        Link 2 (wlp2s0)
            Current Scopes: DNS
                 Protocols: +DefaultRoute +LLMNR -mDNS -DNSOverTLS DNSSEC=no/unsupported
        Current DNS Server: 192.168.1.1
                DNS Servers: 192.168.1.1
                 DNS Domain: lan
    """
    current_iface: InterfaceDns | None = None
    section_is_global = False

    for raw_line in text.splitlines():
        # Detecta inicio de secao
        if re.match(r"^Global\s*$", raw_line.strip()):
            section_is_global = True
            current_iface = None
            continue
        m = re.match(r"^Link\s+\d+\s+\(([^)]+)\)", raw_line.strip())
        if m:
            section_is_global = False
            if current_iface is not None:
                st.interfaces.append(current_iface)
            current_iface = InterfaceDns(name=m.group(1))
            continue

        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("DNS Servers:"):
            servers = line[len("DNS Servers:"):].strip().split()
            if section_is_global:
                st.global_dns = servers
            elif current_iface is not None:
                current_iface.dns_servers = servers
        elif line.startswith("Fallback DNS Servers:") and section_is_global:
            st.fallback_dns = line[len("Fallback DNS Servers:"):].strip().split()
        elif line.startswith("Current DNS Server:"):
            srv = line[len("Current DNS Server:"):].strip()
            if srv:
                st.current_dns.append(srv)
        elif line.startswith("DNS Domain:") and current_iface is not None:
            current_iface.domains = line[len("DNS Domain:"):].strip().split()
        elif line.startswith("Protocols:"):
            # Procura por +/-DNSOverTLS
            m = re.search(r"([+\-])DNSOverTLS", line)
            if m:
                value = "yes" if m.group(1) == "+" else "no"
                if section_is_global:
                    st.global_dot = value
                elif current_iface is not None:
                    current_iface.dns_over_tls = value

    if current_iface is not None:
        st.interfaces.append(current_iface)


# ============================================================
# Set global DNS (editando /etc/systemd/resolved.conf)
# ============================================================


def set_global_dns_elevated(
    servers: list[str],
    dot: bool = True,
    fallback: list[str] | None = None,
) -> tuple[bool, str]:
    """Atualiza /etc/systemd/resolved.conf via pkexec.

    Escreve secao [Resolve] com DNS=, FallbackDNS=, DNSOverTLS=. Depois
    restart do systemd-resolved.
    """
    if not _validate_servers(servers):
        return False, "Lista de DNS servers invalida."

    fallback_str = " ".join(fallback) if fallback else ""
    dns_str = " ".join(servers)
    dot_str = "yes" if dot else "no"

    # Constroi conteudo do .conf (estilo Fedora moderno)
    # Note: preservamos comentarios existentes? Nao — fazemos overwrite simples.
    # O original e' restaurado se voce 'Restaurar padrao'.
    import uuid
    delim = f"DNS_VIGIA_{uuid.uuid4().hex}"
    new_content = "[Resolve]\n"
    new_content += f"DNS={dns_str}\n"
    if fallback_str:
        new_content += f"FallbackDNS={fallback_str}\n"
    new_content += f"DNSOverTLS={dot_str}\n"
    new_content += "# Gerenciado pelo Vigia DNS Manager\n"

    script = f"""set -e
# Backup .original se ainda nao tiver
if [ ! -f /etc/systemd/resolved.conf.vigia-backup ] && [ -f /etc/systemd/resolved.conf ]; then
    cp /etc/systemd/resolved.conf /etc/systemd/resolved.conf.vigia-backup
fi

# Escreve novo conteudo
cat > /etc/systemd/resolved.conf << '{delim}'
{new_content}
{delim}

# Restart pra aplicar
systemctl restart systemd-resolved
"""
    rc, out, err = _run(["pkexec", "bash", "-c", script], timeout=30)
    if rc in (126, 127):
        return False, "Autenticacao cancelada."
    if rc != 0:
        msg = (err or out).strip()
        return False, f"Falha ao aplicar config:\n\n{msg[:500]}"
    return True, ""


def restore_default_elevated() -> tuple[bool, str]:
    """Restaura /etc/systemd/resolved.conf.vigia-backup se existir."""
    script = """set -e
if [ -f /etc/systemd/resolved.conf.vigia-backup ]; then
    mv -f /etc/systemd/resolved.conf.vigia-backup /etc/systemd/resolved.conf
    systemctl restart systemd-resolved
else
    # Sem backup — apenas remove config customizada
    cat > /etc/systemd/resolved.conf << 'DNS_VIGIA_RESET'
# Restaurado pelo Vigia DNS Manager (sem backup anterior).
# Use defaults do systemd-resolved.
[Resolve]
DNS_VIGIA_RESET
    systemctl restart systemd-resolved
fi
"""
    rc, out, err = _run(["pkexec", "bash", "-c", script], timeout=30)
    if rc in (126, 127):
        return False, "Autenticacao cancelada."
    if rc != 0:
        msg = (err or out).strip()
        return False, f"Falha ao restaurar:\n\n{msg[:500]}"
    return True, ""


# ============================================================
# Flush cache
# ============================================================


def flush_cache_elevated() -> tuple[bool, str]:
    """`resolvectl flush-caches` precisa root."""
    rc, out, err = _run(["pkexec", "resolvectl", "flush-caches"], timeout=10)
    if rc in (126, 127):
        return False, "Autenticacao cancelada."
    if rc != 0:
        msg = (err or out).strip()
        return False, f"Falha:\n\n{msg[:300]}"
    return True, ""


# ============================================================
# Test resolver (latency)
# ============================================================


def test_resolver(server: str, timeout: int = 3) -> tuple[bool, str, float]:
    """Roda um lookup contra <server> e mede latencia em ms.

    Usa `getent hosts` ou `dig`/`nslookup` se disponivel.
    Retorna (ok, error_msg, latency_ms).
    """
    if not _validate_servers([server]):
        return False, "IP invalido.", 0.0

    # Usa python pra socket-based lookup com servidor especifico
    # Cara - via dnspython se disponivel, senao via dig
    if shutil.which("dig") is not None:
        t0 = time.monotonic()
        rc, out, err = _run(
            ["dig", "+short", "+time=2", "+tries=1", f"@{server}", "example.com", "A"],
            timeout=timeout + 1,
        )
        latency = (time.monotonic() - t0) * 1000
        if rc == 0 and out.strip():
            return True, "", latency
        return False, "Timeout ou sem resposta.", latency

    return False, "Comando 'dig' nao encontrado.", 0.0


# ============================================================
# Helpers
# ============================================================


_IPV4_RE = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$")
_IPV6_RE = re.compile(r"^[0-9a-fA-F:]+$")


def _validate_servers(servers: list[str]) -> bool:
    if not servers:
        return False
    for s in servers:
        m = _IPV4_RE.match(s)
        if m:
            try:
                octets = [int(o) for o in m.groups()]
                if all(0 <= o <= 255 for o in octets):
                    continue
            except ValueError:
                return False
            return False
        if _IPV6_RE.match(s) and "::" in s or s.count(":") >= 2:
            continue
        return False
    return True
