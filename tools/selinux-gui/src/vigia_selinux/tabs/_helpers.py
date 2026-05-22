"""Helpers compartilhados entre tabs."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


# Largura maxima do conteudo nas tabs (em pixels). Janelas mais largas que
# isso ficam com whitespace nas laterais (conteudo centralizado).
# Mesma convencao que GNOME Settings, GNOME Software, etc.
CONTENT_MAX_WIDTH = 720
CONTENT_TIGHTENING = 600


def make_clamp(child: Gtk.Widget) -> Adw.Clamp:
    """Wrappa um widget em Adw.Clamp para limitar largura em janelas largas."""
    clamp = Adw.Clamp(
        maximum_size=CONTENT_MAX_WIDTH,
        tightening_threshold=CONTENT_TIGHTENING,
    )
    clamp.set_child(child)
    return clamp


def show_error(parent: Gtk.Widget, heading: str, message: str) -> None:
    """Mostra um AlertDialog no top-level window contendo `parent`."""
    win = parent.get_root()
    dlg = Adw.AlertDialog(heading=heading, body=message)
    dlg.add_response("ok", "OK")
    dlg.present(win)


def show_info(parent: Gtk.Widget, heading: str, message: str) -> None:
    win = parent.get_root()
    dlg = Adw.AlertDialog(heading=heading, body=message)
    dlg.add_response("ok", "OK")
    dlg.present(win)
