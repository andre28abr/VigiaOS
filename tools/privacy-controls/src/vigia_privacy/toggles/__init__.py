"""Registro de todos os toggles disponiveis na UI.

Ordem de ALL_TOGGLES define a ordem visual no painel (agrupada por category).
"""

from .bluetooth import TOGGLE as BLUETOOTH
from .dconf_toggles import (
    APP_USAGE,
    CLEAN_TEMP,
    CLEAN_TRASH,
    HIDE_IDENTITY,
    LOCATION,
    LOCK_ENABLED,
    NOTIFICATIONS_IN_LOCK,
    RECENT_FILES,
    TELEMETRY,
)

# Ordem importa — controla a ordem visual e agrupamento por category.
# Toggles da mesma category aparecem juntos no painel.
ALL_TOGGLES = [
    # Localizacao
    LOCATION,
    # Telemetria
    TELEMETRY,
    # Historico
    RECENT_FILES,
    APP_USAGE,
    HIDE_IDENTITY,
    # Lock Screen
    LOCK_ENABLED,
    NOTIFICATIONS_IN_LOCK,
    # Limpeza Automatica
    CLEAN_TRASH,
    CLEAN_TEMP,
    # Dispositivos
    BLUETOOTH,
]
