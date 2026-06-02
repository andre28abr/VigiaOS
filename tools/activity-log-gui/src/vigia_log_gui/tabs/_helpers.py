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
CONTENT_MAX_WIDTH = 1100
CONTENT_TIGHTENING = 900


def make_clamp(child: Gtk.Widget) -> Adw.Clamp:
    """Wrappa widget em Adw.Clamp com as constantes desta tool."""
    return _make_clamp_base(child, CONTENT_MAX_WIDTH, CONTENT_TIGHTENING)


# ============================================================
# Funcoes ESPECIFICAS desta tool — nao migradas para vigia_common
# (sao usadas apenas aqui)
# ============================================================

# Mapas de rotulo/cor por severidade e fonte do evento (consumidos pelas
# abas Timeline e Correlacoes). Restaurados apos a migracao vigia_common
# (commit 66121a6) te-los removido por engano.
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
