"""Catalogo de perfis de scan nmap.

Cada perfil define:
- args: argumentos passados pro nmap (alem de -oX - sempre adicionado)
- needs_root: se requer pkexec
- speed: estimativa qualitativa
- intrusiveness: qual o ruido na rede / risco de tripar IDS
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScanProfile:
    id: str
    name: str
    short_desc: str
    long_desc: str
    args: list[str]
    needs_root: bool = False
    speed: str = "medio"          # "rapido" | "medio" | "lento"
    intrusiveness: str = "medio"  # "baixo" | "medio" | "alto"


PROFILES: list[ScanProfile] = [
    ScanProfile(
        id="ping",
        name="Discovery (ping scan)",
        short_desc="So descobre quais hosts estao vivos. Nenhuma porta escaneada.",
        long_desc=(
            "Modo mais leve. Usa ICMP echo + TCP SYN em 443 + ACK em 80 para "
            "determinar se host responde. Util pra mapear rapidamente uma "
            "subnet (/24 em ~2s). Sem port scan."
        ),
        args=["-sn"],
        needs_root=False,
        speed="rapido",
        intrusiveness="baixo",
    ),
    ScanProfile(
        id="quick",
        name="Quick (top 100 portas)",
        short_desc="Top 100 portas TCP mais comuns. Bom para visao rapida.",
        long_desc=(
            "TCP connect scan nas 100 portas mais comumente abertas (HTTP, "
            "HTTPS, SSH, DNS, etc.). Nao precisa de root. Sem detecao "
            "de versao."
        ),
        args=["-F"],
        needs_root=False,
        speed="rapido",
        intrusiveness="baixo",
    ),
    ScanProfile(
        id="standard",
        name="Standard (top 1000 portas)",
        short_desc="Default do nmap — top 1000 portas + service version.",
        long_desc=(
            "Padrao do nmap. TCP connect scan nas 1000 portas mais comuns + "
            "detecao de versao de servicos (-sV). Util pra reconhecimento "
            "completo de um host conhecido."
        ),
        args=["-sV"],
        needs_root=False,
        speed="medio",
        intrusiveness="medio",
    ),
    ScanProfile(
        id="stealth",
        name="Stealth (SYN scan)",
        short_desc="SYN scan — nao completa handshake. Requer root.",
        long_desc=(
            "Tambem chamado de 'half-open scan'. Envia SYN, recebe SYN-ACK "
            "(porta aberta) ou RST (fechada), envia RST. Nunca completa "
            "3-way handshake — historicamente nao aparecia em logs de "
            "aplicacao. IDS modernos detectam. Precisa root (raw sockets)."
        ),
        args=["-sS", "-sV"],
        needs_root=True,
        speed="medio",
        intrusiveness="medio",
    ),
    ScanProfile(
        id="aggressive",
        name="Aggressive (-A)",
        short_desc="OS detection + version + scripts + traceroute. Demorado.",
        long_desc=(
            "Equivalente a <tt>-A</tt>: OS fingerprinting, detecao de versao "
            "(-sV), scripts NSE default (-sC), traceroute. Muito ruidoso, "
            "facil de detectar. Use so em hosts que voce controla ou tem "
            "autorizacao explicita. Pode levar 1-5 min por host."
        ),
        args=["-A"],
        needs_root=True,
        speed="lento",
        intrusiveness="alto",
    ),
    ScanProfile(
        id="full",
        name="Full (todas as 65535 portas)",
        short_desc="TCP scan completo + service version. Muito lento.",
        long_desc=(
            "Escaneia <tt>-p-</tt> (todas as portas TCP de 1 a 65535) com "
            "detecao de versao. Encontra services que nao usam portas "
            "comuns. Lento: pode levar 30 min ou mais em host com firewall."
        ),
        args=["-p-", "-sV"],
        needs_root=False,
        speed="lento",
        intrusiveness="alto",
    ),
]


def get_profile(profile_id: str) -> ScanProfile | None:
    for p in PROFILES:
        if p.id == profile_id:
            return p
    return None


def default_profile() -> ScanProfile:
    return PROFILES[2]  # standard
