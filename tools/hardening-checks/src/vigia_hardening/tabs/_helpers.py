"""Helpers compartilhados entre tabs do Hardening Checks."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


CONTENT_MAX_WIDTH = 800
CONTENT_TIGHTENING = 600


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


def severity_css_class(score: int | None) -> str:
    """Mapeia hardening_index para classe CSS de cor."""
    if score is None:
        return "dim-label"
    if score >= 75:
        return "success"
    if score >= 50:
        return "warning"
    return "error"


def severity_label(score: int | None) -> str:
    if score is None:
        return "Nao avaliado"
    if score >= 85:
        return "Excelente"
    if score >= 75:
        return "Bom"
    if score >= 60:
        return "Razoavel"
    if score >= 40:
        return "Insuficiente"
    return "Critico"
