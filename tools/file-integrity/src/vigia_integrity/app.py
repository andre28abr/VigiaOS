"""Application root (Adw.Application)."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio  # noqa: E402

from . import __app_id__
from .window import VigiaIntegrityWindow


class VigiaIntegrityApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=__app_id__,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

    def do_activate(self) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        win = self.get_active_window()
        if win is None:
            win = VigiaIntegrityWindow(self)
        win.present()
