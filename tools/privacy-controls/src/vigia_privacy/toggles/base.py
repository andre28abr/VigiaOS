"""Base abstrata para toggles de privacidade.

Cada toggle implementa:
- `name`: rotulo curto (mostrado na linha do switch)
- `description`: explicacao 1-2 linhas (mostrado abaixo do rotulo, em dim)
- `category`: grupo logico ("Localizacao", "Telemetria", "Dispositivos")
- `is_enabled()`: le estado atual do sistema (True = ativo)
- `set_enabled(bool)`: muda estado do sistema
- `is_available()`: True se o toggle pode ser usado neste sistema
  (ex: bluetooth so faz sentido em maquinas com adapter)

Helper `dconf_toggle()` facilita a criacao de toggles que mapeiam
direto para uma chave dconf — a grande maioria dos casos.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from gi.repository import Gio


@dataclass
class Toggle:
    name: str
    description: str
    category: str
    get_fn: Callable[[], bool]
    set_fn: Callable[[bool], None]
    available_fn: Callable[[], bool] = lambda: True

    def is_enabled(self) -> bool:
        try:
            return self.get_fn()
        except Exception:
            return False

    def set_enabled(self, value: bool) -> None:
        self.set_fn(value)

    def is_available(self) -> bool:
        try:
            return self.available_fn()
        except Exception:
            return False


def dconf_toggle(
    *,
    schema: str,
    key: str,
    name: str,
    description: str,
    category: str,
    invert: bool = False,
) -> Toggle:
    """Cria um Toggle que mapeia para uma chave dconf booleana.

    invert=True faz o toggle exibido representar o OPOSTO do valor armazenado.
    Util quando a semantica "toggle ON = privacidade ativa" inverte a do dconf
    (ex: dconf 'remember-recent-files=true' significa 'lembrar', mas o toggle
    de privacidade "Nao lembrar" deve estar ON quando isso for false).
    """

    def _get() -> bool:
        raw = Gio.Settings.new(schema).get_boolean(key)
        return (not raw) if invert else raw

    def _set(value: bool) -> None:
        stored = (not value) if invert else value
        Gio.Settings.new(schema).set_boolean(key, stored)

    def _available() -> bool:
        src = Gio.SettingsSchemaSource.get_default()
        if src is None:
            return False
        schema_obj = src.lookup(schema, recursive=True)
        if schema_obj is None:
            return False
        # Verifica tambem que a key existe no schema (algumas chaves foram
        # removidas em versoes mais novas do GNOME)
        return schema_obj.has_key(key)

    return Toggle(
        name=name,
        description=description,
        category=category,
        get_fn=_get,
        set_fn=_set,
        available_fn=_available,
    )
