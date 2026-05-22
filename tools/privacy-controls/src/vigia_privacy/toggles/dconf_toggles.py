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
    name="Servicos de localizacao",
    description="Quando OFF, apps GNOME nao podem usar GPS, redes WiFi proximas "
    "ou IP para inferir sua localizacao.",
    category="Localizacao",
)

# ============================================================================
# Telemetria
# ============================================================================

TELEMETRY = dconf_toggle(
    schema="org.gnome.desktop.privacy",
    key="report-technical-problems",
    name="Bloquear relatorios tecnicos do GNOME",
    description="Quando ON, GNOME nao envia relatorios anonimos de crashes "
    "ou estatisticas de uso. Equivalente a 'opt-out' de telemetria.",
    category="Telemetria",
    invert=True,
)

# ============================================================================
# Historico (rastros locais do uso)
# ============================================================================

RECENT_FILES = dconf_toggle(
    schema="org.gnome.desktop.privacy",
    key="remember-recent-files",
    name="Nao lembrar arquivos recentes",
    description="Quando ON, apps GNOME nao mostram historico de arquivos "
    "abertos em 'Recent'. Util para uso em maquinas compartilhadas.",
    category="Historico",
    invert=True,
)

APP_USAGE = dconf_toggle(
    schema="org.gnome.desktop.privacy",
    key="remember-app-usage",
    name="Nao lembrar uso de aplicativos",
    description="Quando ON, GNOME nao registra estatisticas de quanto tempo "
    "voce usa cada app (afeta sugestoes em Search e Activities).",
    category="Historico",
    invert=True,
)

HIDE_IDENTITY = dconf_toggle(
    schema="org.gnome.desktop.privacy",
    key="hide-identity",
    name="Esconder identidade em arquivos compartilhados",
    description="Quando ON, remove metadados como nome e hostname ao "
    "compartilhar arquivos via apps GNOME.",
    category="Historico",
)

# ============================================================================
# Lock Screen
# ============================================================================

LOCK_ENABLED = dconf_toggle(
    schema="org.gnome.desktop.screensaver",
    key="lock-enabled",
    name="Bloquear tela automaticamente",
    description="Quando ON, a tela e' bloqueada apos o periodo idle "
    "configurado em GNOME Settings.",
    category="Lock Screen",
)

NOTIFICATIONS_IN_LOCK = dconf_toggle(
    schema="org.gnome.desktop.notifications",
    key="show-in-lock-screen",
    name="Esconder previa de notificacoes na lock screen",
    description="Quando ON, notificacoes aparecem na lock screen apenas como "
    "'(N notificacoes novas)' sem conteudo legivel.",
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
    description="Quando ON, arquivos na lixeira sao apagados apos o periodo "
    "configurado em Settings (default: 30 dias). Evita acumular rastros.",
    category="Limpeza Automatica",
)

CLEAN_TEMP = dconf_toggle(
    schema="org.gnome.desktop.privacy",
    key="remove-old-temp-files",
    name="Limpar arquivos temporarios automaticamente",
    description="Quando ON, arquivos em /tmp e similares sao limpos apos "
    "o periodo configurado.",
    category="Limpeza Automatica",
)
