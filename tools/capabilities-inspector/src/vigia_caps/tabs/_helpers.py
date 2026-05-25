"""Helpers compartilhados."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


CONTENT_MAX_WIDTH = 860
CONTENT_TIGHTENING = 680


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


def show_info(parent: Gtk.Widget, heading: str, message: str) -> None:
    win = parent.get_root()
    dlg = Adw.AlertDialog(heading=heading, body=message)
    dlg.add_response("ok", "OK")
    dlg.present(win)


def risk_css(risk: str) -> str:
    """Mapeia risco -> CSS class."""
    return {
        "alto": "error",
        "medio": "warning",
        "baixo": "success",
    }.get(risk, "dim-label")


def escape_markup(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
