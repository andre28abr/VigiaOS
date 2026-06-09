"""Humaniza o output do `ss`: estados em PT-BR, glossário de portas, detecção
de loopback/internet e DNS reverso (em cache).

Puro/testável — o `resolve_host` toca a rede mas só é chamado em thread, e o
cache evita repetição. O resto (rótulos, split, glossário) é função pura.
"""

from __future__ import annotations

import socket

# ============================================================
# Estados do ss → português
# ============================================================

STATE_LABELS = {
    "ESTAB": "Conectado",
    "LISTEN": "Escutando",
    "TIME-WAIT": "Encerrando",
    "CLOSE-WAIT": "Encerrando",
    "FIN-WAIT-1": "Encerrando",
    "FIN-WAIT-2": "Encerrando",
    "LAST-ACK": "Encerrando",
    "CLOSING": "Encerrando",
    "UNCONN": "Inativo",
    "SYN-SENT": "Conectando",
    "SYN-RECV": "Conectando",
}


def state_label(state: str) -> str:
    return STATE_LABELS.get(state, state.capitalize())


# ============================================================
# host:port
# ============================================================


def split_host_port(addr: str) -> tuple[str, str]:
    """'192.168.0.5:443' → ('192.168.0.5','443'); '[::1]:53' → ('::1','53')."""
    if not addr:
        return ("", "")
    if addr.startswith("["):  # IPv6 entre colchetes
        host, _, port = addr.partition("]")
        return (host[1:], port.lstrip(":"))
    host, sep, port = addr.rpartition(":")
    if not sep:  # sem ':' → tudo é host
        return (addr, "")
    return (host, port)


# ============================================================
# loopback / internet
# ============================================================


def is_loopback(addr: str) -> bool:
    host, _ = split_host_port(addr)
    h = host.strip("[]")
    return h.startswith("127.") or h == "::1" or h == "localhost"


def is_internet_peer(addr: str) -> bool:
    """True se o destino é um IP remoto de verdade (não loopback nem wildcard
    de socket escutando)."""
    host, _ = split_host_port(addr)
    h = host.strip("[]")
    if not h or h in ("*", "0.0.0.0", "::"):
        return False
    if h.startswith("127.") or h == "::1":
        return False
    return True


# ============================================================
# Glossário de portas comuns (aba Escutando)
# ============================================================

PORT_GLOSSARY = {
    "22": "Acesso remoto (SSH)",
    "53": "DNS — resolução de nomes",
    "80": "Web (HTTP)",
    "443": "Web seguro (HTTPS)",
    "631": "Impressão (CUPS)",
    "5353": "Descoberta de rede (mDNS/Bonjour)",
    "5355": "Descoberta de nomes (LLMNR)",
    "139": "Compartilhamento Windows (NetBIOS)",
    "445": "Compartilhamento de arquivos (SMB)",
    "3389": "Área de trabalho remota (RDP)",
    "25": "E-mail (SMTP)",
    "587": "E-mail — envio (SMTP)",
    "465": "E-mail — envio seguro",
    "993": "E-mail (IMAP seguro)",
    "143": "E-mail (IMAP)",
    "110": "E-mail (POP3)",
    "67": "Rede (DHCP)",
    "68": "Rede (DHCP)",
    "123": "Relógio (NTP)",
    "548": "Compartilhamento Apple (AFP)",
    "1714": "KDE Connect (celular ↔ PC)",
    "1716": "KDE Connect (celular ↔ PC)",
    "8080": "Web alternativa (proxy/desenvolvimento)",
    "3306": "Banco de dados (MySQL)",
    "5432": "Banco de dados (PostgreSQL)",
    "6379": "Banco de dados (Redis)",
    "27017": "Banco de dados (MongoDB)",
}


def port_hint(port: str) -> str:
    return PORT_GLOSSARY.get(port, "")


# ============================================================
# DNS reverso (cache)
# ============================================================

_DNS_CACHE: dict[str, str] = {}


def resolve_host(ip: str) -> str:
    """DNS reverso (PTR) com cache. '' se não resolver. BLOQUEIA (resolver da
    rede) — chamar sempre em thread, nunca no UI."""
    if not ip:
        return ""
    if ip in _DNS_CACHE:
        return _DNS_CACHE[ip]
    name = ""
    try:
        name = socket.gethostbyaddr(ip)[0]
    except (OSError, socket.herror, socket.gaierror, UnicodeError):
        name = ""
    _DNS_CACHE[ip] = name
    return name
