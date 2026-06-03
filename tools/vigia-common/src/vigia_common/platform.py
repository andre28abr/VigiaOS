"""Plataforma: Fedora Workstation (dnf).

O VigiaOS roda em **Fedora Workstation** (tradicional, com ``dnf``) — instala
pacotes na hora, sem reboot.

> Histórico: o projeto começou em Fedora Atomic/Silverblue, mas **migrou de vez
> para o Workstation** (toolchain de forense + velocidade de iteração) — ver
> README/DEVELOPMENT. Estas funções são o **ponto único** do gerenciador de
> pacotes e das dicas de instalação.
"""

from __future__ import annotations


def package_manager() -> str:
    """Gerenciador de pacotes do sistema: ``dnf`` (Fedora Workstation)."""
    return "dnf"


def needs_reboot_to_apply() -> bool:
    """``False`` — o ``dnf`` aplica na hora, sem reboot."""
    return False


def install_hint(*packages: str, reboot: bool = True) -> str:
    """Comando pra instalar pacotes no Fedora Workstation.

    ``sudo dnf install <pkgs>`` (aplica na hora, sem reboot). O parâmetro
    ``reboot`` é ignorado (mantido por compatibilidade de assinatura).
    """
    pkgs = " ".join(packages)
    return f"sudo dnf install {pkgs}"
