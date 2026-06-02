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
    make_clamp as _make_clamp_base,
)

# Customizado para esta tool (largura/aperto do clamp)
CONTENT_MAX_WIDTH = 1100
CONTENT_TIGHTENING = 900


def make_clamp(child: Gtk.Widget) -> Adw.Clamp:
    """Wrappa widget em Adw.Clamp com as constantes desta tool."""
    return _make_clamp_base(child, CONTENT_MAX_WIDTH, CONTENT_TIGHTENING)


# ============================================================
# Funcoes ESPECIFICAS desta tool — nao migradas para vigia_common
# (sao usadas apenas aqui)
# ============================================================

def risk_css(risk: str) -> str:
    """Mapeia risco -> CSS class."""
    return {
        "alto": "error",
        "medio": "warning",
        "baixo": "success",
    }.get(risk, "dim-label")

def escape_markup(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
