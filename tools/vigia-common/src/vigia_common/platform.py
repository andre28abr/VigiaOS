"""Plataforma: Fedora Workstation (dnf).

O VigiaOS roda em **Fedora Workstation** (tradicional, com ``dnf``) — instala
pacotes na hora, sem reboot.

> Histórico: o projeto começou em Fedora Atomic/Silverblue, mas **migrou de vez
> para o Workstation** (toolchain de forense + velocidade de iteração) — ver
> README/DEVELOPMENT. ``is_atomic()`` permanece por compatibilidade durante a
> transição, **sempre retornando ``False``**; os poucos ramos "atômicos"
> remanescentes nos chamadores são código morto a ser removido nas próximas
> fases. Estas funções continuam como **ponto único** do gerenciador de pacotes
> e das dicas de instalação.
"""

from __future__ import annotations


def is_atomic() -> bool:
    """Sempre ``False`` — o VigiaOS roda em Fedora Workstation (dnf).

    Mantida durante a migração do Silverblue → Workstation para não quebrar
    os chamadores que ainda a importam; será removida quando todos deixarem
    de depender dela.
    """
    return False


def package_manager() -> str:
    """Gerenciador de pacotes do sistema: ``dnf`` (Fedora Workstation)."""
    return "rpm-ostree" if is_atomic() else "dnf"


def needs_reboot_to_apply() -> bool:
    """True se instalar/remover pacotes exige reboot — ``False`` no Workstation."""
    return is_atomic()


def install_hint(*packages: str, reboot: bool = True) -> str:
    """Sugestão de comando pra instalar pacotes no Fedora Workstation.

    ``sudo dnf install <pkgs>`` (aplica na hora, sem reboot). Use em mensagens
    "instale o backend X" pra mostrar o comando certo pro usuário.
    """
    pkgs = " ".join(packages)
    if is_atomic():
        cmd = f"rpm-ostree install {pkgs}"
        return f"{cmd} && systemctl reboot" if reboot else cmd
    return f"sudo dnf install {pkgs}"
