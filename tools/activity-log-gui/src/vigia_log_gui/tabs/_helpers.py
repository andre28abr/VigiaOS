"""Helpers compartilhados entre tabs."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


CONTENT_MAX_WIDTH = 960  # Timeline precisa de largura para narratives compridas
CONTENT_TIGHTENING = 760


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


SEVERITY_CSS = {
    "suspicious": "error",
    "interesting": "warning",
    "routine": "dim-label",
}


SEVERITY_LABEL = {
    "suspicious": "SUSP",
    "interesting": "INFO",
    "routine": "OK",
}


SOURCE_LABEL = {
    "audit": "AUDIT",
    "journal": "JRNL",
    "fail2ban": "F2B",
}


def severity_css(sev: str) -> str:
    return SEVERITY_CSS.get(sev, "dim-label")


def severity_label(sev: str) -> str:
    return SEVERITY_LABEL.get(sev, sev.upper()[:5])


def source_label(src: str) -> str:
    return SOURCE_LABEL.get(src, src.upper()[:5])


def escape_markup(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
