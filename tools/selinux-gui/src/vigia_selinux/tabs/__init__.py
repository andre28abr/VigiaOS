"""Tabs do Vigia SELinux GUI.

Cada modulo expoe uma classe (subclass de Gtk.Widget) e e' instanciada
em window.py e adicionada ao Adw.ViewStack.
"""

from .booleans import BooleansTab
from .denials import DenialsTab
from .files import FilesTab
from .network import NetworkTab
from .processes import ProcessesTab
from .status import StatusTab

__all__ = [
    "StatusTab",
    "BooleansTab",
    "DenialsTab",
    "FilesTab",
    "NetworkTab",
    "ProcessesTab",
]
