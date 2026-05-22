"""Helpers compartilhados entre tabs do netmon."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


CONTENT_MAX_WIDTH = 900  # netmon precisa de mais largura para tabelas
CONTENT_TIGHTENING = 700


def make_clamp(child: Gtk.Widget) -> Adw.Clamp:
    clamp = Adw.Clamp(
        maximum_size=CONTENT_MAX_WIDTH,
        tightening_threshold=CONTENT_TIGHTENING,
    )
    clamp.set_child(child)
    return clamp


def show_error(parent: Gtk.Widget, heading: str, message: str) -> None:
    win = parent.get_root()
    dlg = Adw.AlertDialog(heading=heading, body=message)
    dlg.add_response("ok", "OK")
    dlg.present(win)
