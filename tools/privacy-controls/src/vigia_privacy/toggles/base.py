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

import shutil
import subprocess
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


def systemd_unit_toggle(
    *,
    unit: str,
    name: str,
    description: str,
    category: str,
    extra_available_check: Callable[[], bool] | None = None,
) -> Toggle:
    """Toggle controlando active/inactive + enabled/disabled de uma unit systemd.

    - Read state: chama 'systemctl is-active <unit>' (sem privilegio)
    - Write state: chama 'pkexec systemctl enable/disable --now <unit>'
      (--now = enable+start ou disable+stop em uma chamada).
      pkexec abre o dialogo grafico do polkit pedindo senha admin.

    `extra_available_check` permite condicoes adicionais (ex: 'tor' so' aparece
    se o binario tor estiver instalado, alem da unit existir).
    """

    def _get() -> bool:
        result = subprocess.run(
            ["systemctl", "is-active", unit],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() == "active"

    def _set(value: bool) -> None:
        if shutil.which("pkexec") is None:
            raise RuntimeError(
                "pkexec não encontrado. Instale 'polkit' via rpm-ostree."
            )
        action = "enable" if value else "disable"
        result = subprocess.run(
            ["pkexec", "systemctl", action, "--now", f"{unit}.service"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            # Distingue cancelamento (usuario nao deu senha) de outro erro
            stderr = result.stderr.strip() or result.stdout.strip()
            if "Request dismissed" in stderr or result.returncode == 126:
                raise RuntimeError("Autenticação cancelada pelo usuário.")
            raise RuntimeError(f"systemctl {action} --now {unit} falhou: {stderr}")

    def _available() -> bool:
        # Unit existe no sistema?
        check = subprocess.run(
            ["systemctl", "list-unit-files", f"{unit}.service", "--no-legend"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if check.returncode != 0 or not check.stdout.strip():
            return False
        # Filtro adicional opcional
        if extra_available_check is not None:
            try:
                return extra_available_check()
            except Exception:
                return False
        return True

    return Toggle(
        name=name,
        description=description,
        category=category,
        get_fn=_get,
        set_fn=_set,
        available_fn=_available,
    )
