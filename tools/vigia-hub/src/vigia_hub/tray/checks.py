"""Detecta se o tray icon pode funcionar.

Dependencias:
- libayatana-appindicator-gtk3 (lib C + binding GI)
- gnome-shell-extension-appindicator (extensao GNOME que renderiza)

Em Silverblue vanilla, NENHUM dos dois vem instalado. Em Bluefin/Aurora
ja' vem por default. Pra Silverblue precisa:

    pkexec rpm-ostree install libayatana-appindicator-gtk3 \\
                              gnome-shell-extension-appindicator

E reboot (overlay rpm-ostree).

Apos instalado, a extensao precisa ser ATIVADA:
    gnome-extensions enable appindicatorsupport@rgcjonas.gmail.com
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional


# Pacotes necessarios em Fedora Silverblue/Atomic
INSTALL_PACKAGES = [
    "libayatana-appindicator-gtk3",
    "gnome-shell-extension-appindicator",
]

EXT_UUID = "appindicatorsupport@rgcjonas.gmail.com"


@dataclass
class TrayCheck:
    """Resultado do teste de viabilidade do tray."""
    ok: bool
    has_lib: bool
    has_extension: bool
    ext_enabled: bool
    error_msg: str = ""


def appindicator_lib_available() -> bool:
    """Testa se libayatana-appindicator-gtk3 esta instalada.

    Faz import lazy num subprocess pra nao poluir o processo atual com
    PyGObject GTK3 (que conflitaria com GTK4).
    """
    code = (
        "import gi; "
        "gi.require_version('AyatanaAppIndicator3', '0.1'); "
        "from gi.repository import AyatanaAppIndicator3"
    )
    try:
        result = subprocess.run(
            ["python3", "-c", code],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def appindicator_extension_enabled() -> tuple[bool, bool]:
    """Retorna (instalada, ativa) da extensao AppIndicator do GNOME.

    Usa `gnome-extensions info <uuid>` que retorna exit 0 e mostra
    "State: ENABLED" no stdout se ativa.
    """
    if not shutil.which("gnome-extensions"):
        return (False, False)
    try:
        result = subprocess.run(
            ["gnome-extensions", "info", EXT_UUID],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return (False, False)
    if result.returncode != 0:
        return (False, False)
    out = result.stdout.upper()
    installed = True
    enabled = "STATE: ENABLED" in out or "STATE: ACTIVE" in out
    return (installed, enabled)


def tray_can_work() -> TrayCheck:
    """Verifica tudo de uma vez. Retorna TrayCheck com diagnostico."""
    has_lib = appindicator_lib_available()
    has_ext, ext_enabled = appindicator_extension_enabled()

    if has_lib and has_ext and ext_enabled:
        return TrayCheck(
            ok=True, has_lib=True, has_extension=True, ext_enabled=True
        )

    missing = []
    if not has_lib:
        missing.append("libayatana-appindicator-gtk3 (biblioteca)")
    if not has_ext:
        missing.append("gnome-shell-extension-appindicator (extensao)")
    elif not ext_enabled:
        missing.append("extensao AppIndicator esta instalada mas desativada")

    return TrayCheck(
        ok=False,
        has_lib=has_lib,
        has_extension=has_ext,
        ext_enabled=ext_enabled,
        error_msg="; ".join(missing),
    )


def install_command() -> list[str]:
    """Comando pra instalar os pacotes (pkexec rpm-ostree install ...)."""
    return ["pkexec", "rpm-ostree", "install"] + INSTALL_PACKAGES


def enable_extension_command() -> list[str]:
    """Comando pra ativar a extensao."""
    return ["gnome-extensions", "enable", EXT_UUID]
