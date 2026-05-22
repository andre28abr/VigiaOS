"""Toggles disponiveis. Cada modulo expoe `TOGGLE` (instancia de Toggle)."""

from .bluetooth import TOGGLE as BLUETOOTH
from .location import TOGGLE as LOCATION
from .telemetry import TOGGLE as TELEMETRY

# Ordem importa — controla ordem visual no painel
ALL_TOGGLES = [
    LOCATION,
    TELEMETRY,
    BLUETOOTH,
]
