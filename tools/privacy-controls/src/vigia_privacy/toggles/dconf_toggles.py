"""Toggles user-scope via dconf.

Todos sao mapeamentos diretos para chaves dconf booleanas. O helper
`dconf_toggle()` cuida da boilerplate de get/set/available.

Convencoes de semantica:
- O toggle exibido na UI representa **privacidade ativa**.
- Quando o nome dconf NAO bate com essa semantica (ex: 'remember-X'),
  usamos `invert=True`.
"""

from .base import dconf_toggle

# ============================================================================
# Localizacao
# ============================================================================

LOCATION = dconf_toggle(
    schema="org.gnome.system.location",
    key="enabled",
    name="Serviços de localização",
    description="Quando OFF, apps GNOME não podem usar GPS, redes WiFi próximas "
    "ou IP para inferir sua localização.",
    category="Localização",
)

# ============================================================================
# Telemetria
# ============================================================================

TELEMETRY = dconf_toggle(
    schema="org.gnome.desktop.privacy",
    key="report-technical-problems",
    name="Bloquear relatórios técnicos do GNOME",
    description="Quando ON, GNOME não envia relatórios anônimos de crashes "
    "ou estatísticas de uso. Equivalente a 'opt-out' de telemetria.",
    category="Telemetria",
    invert=True,
)

# ============================================================================
# Historico (rastros locais do uso)
# ============================================================================

RECENT_FILES = dconf_toggle(
    schema="org.gnome.desktop.privacy",
    key="remember-recent-files",
    name="Não lembrar arquivos recentes",
    description="Quando ON, apps GNOME não mostram histórico de arquivos "
    "abertos em 'Recent'. Útil para uso em máquinas compartilhadas.",
    category="Histórico",
    invert=True,
)

APP_USAGE = dconf_toggle(
    schema="org.gnome.desktop.privacy",
    key="remember-app-usage",
    name="Não lembrar uso de aplicativos",
    description="Quando ON, GNOME não registra estatísticas de quanto tempo "
    "você usa cada app (afeta sugestões em Search e Activities).",
    category="Histórico",
    invert=True,
)

HIDE_IDENTITY = dconf_toggle(
    schema="org.gnome.desktop.privacy",
    key="hide-identity",
    name="Esconder identidade em arquivos compartilhados",
    description="Quando ON, remove metadados como nome e hostname ao "
    "compartilhar arquivos via apps GNOME.",
    category="Histórico",
)

# ============================================================================
# Lock Screen
# ============================================================================

LOCK_ENABLED = dconf_toggle(
    schema="org.gnome.desktop.screensaver",
    key="lock-enabled",
    name="Bloquear tela automaticamente",
    description="Quando ON, a tela é bloqueada após o período idle "
    "configurado em GNOME Settings.",
    category="Lock Screen",
)

NOTIFICATIONS_IN_LOCK = dconf_toggle(
    schema="org.gnome.desktop.notifications",
    key="show-in-lock-screen",
    name="Esconder prévia de notificações na lock screen",
    description="Quando ON, notificações aparecem na lock screen apenas como "
    "'(N notificações novas)' sem conteúdo legível.",
    category="Lock Screen",
    invert=True,
)

# ============================================================================
# Limpeza automatica
# ============================================================================

CLEAN_TRASH = dconf_toggle(
    schema="org.gnome.desktop.privacy",
    key="remove-old-trash-files",
    name="Esvaziar lixeira automaticamente",
    description="Quando ON, arquivos na lixeira são apagados após o período "
    "configurado em Settings (default: 30 dias). Evita acumular rastros.",
    category="Limpeza Automática",
)

CLEAN_TEMP = dconf_toggle(
    schema="org.gnome.desktop.privacy",
    key="remove-old-temp-files",
    name="Limpar arquivos temporários automaticamente",
    description="Quando ON, arquivos em /tmp e similares são limpos após "
    "o período configurado.",
    category="Limpeza Automática",
)
