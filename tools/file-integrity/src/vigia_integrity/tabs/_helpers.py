"""Helpers especificos desta tool.

Re-exporta de `vigia_common.helpers` (mantem compat com codigo
existente que usa `from .._helpers import ...`).
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

# Funcoes compartilhadas via vigia_common (1 fonte unica)
from vigia_common.helpers import (
    show_error,
    show_info,
    copy_to_clipboard,
    make_clamp as _make_clamp_base,
    make_file_picker_row as _make_file_picker_row_base,
)

# Customizado para esta tool (largura/aperto do clamp)
CONTENT_MAX_WIDTH = 800
CONTENT_TIGHTENING = 600


def make_clamp(child: Gtk.Widget) -> Adw.Clamp:
    """Wrappa widget em Adw.Clamp com as constantes desta tool."""
    return _make_clamp_base(child, CONTENT_MAX_WIDTH, CONTENT_TIGHTENING)


def make_file_picker_row(
    title: str, entry: Gtk.Entry, folder_only: bool = False,
):
    """Re-export de vigia_common.helpers.make_file_picker_row.

    Adicionado na merge v0.2.0 (vindo do Hash Tools).
    """
    return _make_file_picker_row_base(title, entry, folder_only=folder_only)
