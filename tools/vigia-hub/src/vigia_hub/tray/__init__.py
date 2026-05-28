"""Tray icon do Vigia Hub.

Arquitetura: o Hub e' GTK4 (libadwaita) mas o tray icon do GNOME exige
'libayatana-appindicator3' que e' GTK3. Como GTK3 e GTK4 NAO podem
coexistir num mesmo processo PyGObject, o tray icon roda como
subprocess separado.

Componentes:
- checks.py  -> funcoes puras pra detectar lib/extensao (testaveis)
- manager.py -> spawna subprocess do indicator (chamado pelo Hub GTK4)
- indicator.py -> script standalone GTK3 que cria o icone

Comunicacao tray -> Hub via D-Bus:
- O Hub e' Adw.Application com application_id "br.com.vigia.Hub"
- Registra Gio.SimpleAction 'show-window', 'show-settings', 'quit-hub'
- Tray invoca essas actions via Gio.DBusActionGroup

Comunicacao Hub -> tray:
- Hub mata subprocess via SIGTERM no shutdown ou quando user desliga
"""

from __future__ import annotations

from .checks import (
    appindicator_lib_available,
    appindicator_extension_enabled,
    tray_can_work,
    INSTALL_PACKAGES,
)
from .manager import TrayManager

__all__ = [
    "TrayManager",
    "appindicator_lib_available",
    "appindicator_extension_enabled",
    "tray_can_work",
    "INSTALL_PACKAGES",
]
