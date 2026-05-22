"""Base abstrata para toggles de privacidade.

Cada toggle implementa:
- `name`: rotulo curto (mostrado na linha do switch)
- `description`: explicacao 1-2 linhas (mostrado abaixo do rotulo, em dim)
- `category`: grupo logico ("Localizacao", "Telemetria", "Dispositivos")
- `is_enabled()`: le estado atual do sistema (True = ativo)
- `set_enabled(bool)`: muda estado do sistema
- `is_available()`: True se o toggle pode ser usado neste sistema
  (ex: bluetooth so faz sentido em maquinas com adapter)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


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
