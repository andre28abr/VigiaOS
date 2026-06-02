"""Helpers especificos desta tool — re-export vigia_common."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from vigia_common.helpers import (
    show_error,
    show_info,
    make_clamp as _make_clamp_base,
)

CONTENT_MAX_WIDTH = 1100
CONTENT_TIGHTENING = 900


def make_clamp(child: Gtk.Widget) -> Adw.Clamp:
    return _make_clamp_base(child, CONTENT_MAX_WIDTH, CONTENT_TIGHTENING)
