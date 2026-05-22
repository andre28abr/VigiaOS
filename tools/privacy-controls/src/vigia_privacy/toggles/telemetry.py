"""Toggle: telemetria/relato de uso do GNOME.

GNOME Software tem uma flag de envio anonimo de stats. Nao e' 'telemetry'
no sentido pesado, mas e' a coisa mais proxima de 'opt-out de coleta'
disponivel via dconf.
"""

from gi.repository import Gio

from .base import Toggle

# Multiplas chaves controlam aspectos diferentes de "report stats":
# - org.gnome.desktop.privacy report-technical-problems
# - org.gnome.software download-updates-notify (ja eh outra coisa)
# Para v0.1 usamos a chave mais explicita.
_SCHEMA = "org.gnome.desktop.privacy"
_KEY = "report-technical-problems"


def _get() -> bool:
    # A semantica do toggle e' INVERTIDA: ativar o toggle = PRIVADO = NAO reportar.
    # Logo, retornamos NOT do valor real ("envia relatorios").
    return not Gio.Settings.new(_SCHEMA).get_boolean(_KEY)


def _set(value: bool) -> None:
    # toggle ON -> PRIVADO -> nao reportar -> set raw key para FALSE
    Gio.Settings.new(_SCHEMA).set_boolean(_KEY, not value)


def _available() -> bool:
    src = Gio.SettingsSchemaSource.get_default()
    return src is not None and src.lookup(_SCHEMA, recursive=True) is not None


TOGGLE = Toggle(
    name="Bloquear relatorios tecnicos do GNOME",
    description="Quando ON, GNOME nao envia relatorios anonimos de crashes "
    "ou estatisticas de uso. Equivalente a 'opt-out' de telemetria.",
    category="Telemetria",
    get_fn=_get,
    set_fn=_set,
    available_fn=_available,
)
