"""Toggle: GNOME location services (geoclue)."""

from gi.repository import Gio

from .base import Toggle

_SCHEMA = "org.gnome.system.location"
_KEY = "enabled"


def _get() -> bool:
    return Gio.Settings.new(_SCHEMA).get_boolean(_KEY)


def _set(value: bool) -> None:
    Gio.Settings.new(_SCHEMA).set_boolean(_KEY, value)


def _available() -> bool:
    # Schema vem com o gnome-control-center; presente em qualquer GNOME desktop.
    src = Gio.SettingsSchemaSource.get_default()
    return src is not None and src.lookup(_SCHEMA, recursive=True) is not None


TOGGLE = Toggle(
    name="Servicos de localizacao",
    description="Quando OFF, apps GNOME nao podem usar GPS, redes WiFi proximas "
    "ou IP para inferir sua localizacao.",
    category="Localizacao",
    get_fn=_get,
    set_fn=_set,
    available_fn=_available,
)
