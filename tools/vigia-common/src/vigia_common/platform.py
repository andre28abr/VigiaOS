"""Detecção de plataforma: sistema atômico (ostree) vs tradicional (dnf).

O VigiaOS roda tanto em **Fedora Atomic** (Silverblue, Kinoite, Bluefin,
Bazzite, Aurora) quanto em **Fedora Workstation** tradicional. A diferença
que importa para a suíte é o gerenciador de pacotes:

- Atômico  → ``rpm-ostree`` (instala em camada, precisa reboot).
- Tradicional → ``dnf`` (instala na hora, sem reboot).

Algumas tools (ex: Deployments Manager) só fazem sentido em sistema
atômico — o Hub usa ``is_atomic()`` para escondê-las no Workstation.
"""

from __future__ import annotations

import os
import shutil

# Marcador criado pelo ostree no boot — presente em Silverblue/Kinoite/etc.,
# ausente no Workstation tradicional. É o sinal canônico de "sistema atômico".
_OSTREE_MARKER = "/run/ostree-booted"


def is_atomic() -> bool:
    """True se o sistema é Fedora Atomic (ostree-based).

    Checa primeiro o marcador ``/run/ostree-booted``. Como fallback
    defensivo (marcador ausente por algum motivo), considera atômico se
    ``rpm-ostree`` existe **e** o diretório ``/ostree`` está presente.
    """
    if os.path.exists(_OSTREE_MARKER):
        return True
    return shutil.which("rpm-ostree") is not None and os.path.isdir("/ostree")


def package_manager() -> str:
    """Nome do gerenciador de pacotes do sistema: ``rpm-ostree`` ou ``dnf``."""
    return "rpm-ostree" if is_atomic() else "dnf"


def needs_reboot_to_apply() -> bool:
    """True se instalar/remover pacotes exige reboot (só em atômico)."""
    return is_atomic()
