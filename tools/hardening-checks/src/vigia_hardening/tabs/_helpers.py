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
    make_clamp as _make_clamp_base,
)

# Customizado para esta tool (largura/aperto do clamp)
CONTENT_MAX_WIDTH = 800
CONTENT_TIGHTENING = 600


def make_clamp(child: Gtk.Widget) -> Adw.Clamp:
    """Wrappa widget em Adw.Clamp com as constantes desta tool."""
    return _make_clamp_base(child, CONTENT_MAX_WIDTH, CONTENT_TIGHTENING)


# ============================================================
# Funcoes ESPECIFICAS desta tool — nao migradas para vigia_common
# (sao usadas apenas aqui)
# ============================================================

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
