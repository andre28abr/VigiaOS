"""Registry das ferramentas da Vigia Suite.

Para adicionar uma ferramenta nova: cria uma `ToolEntry` e adiciona em `TOOLS`.
Ordem na lista controla ordem visual no hub.

Cada tool sabe se precisa de terminal (CLI) ou roda direto (GUI), e se precisa
de root (entao prefix com sudo).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ToolEntry:
    id: str
    name: str
    description: str
    icon: str  # nome do icon a procurar nos icon paths do GNOME
    exec_cmd: list[str]
    needs_terminal: bool = False
    needs_root: bool = False
    available_fn: Callable[[], bool] = field(default=lambda: True)

    def is_available(self) -> bool:
        try:
            return self.available_fn()
        except Exception:
            return False


# ============================================================================
# Tools registry
# ============================================================================

TOOLS: list[ToolEntry] = [
    ToolEntry(
        id="activity-log",
        name="Activity Log",
        description="Visualizador de logs do sistema (audit, journald, fail2ban) "
        "com narrativa human-readable, correlations e live tail.",
        icon="vigia-log",
        exec_cmd=["vigia-log", "--sources", "audit", "journald", "fail2ban"],
        needs_terminal=True,
        needs_root=True,
        available_fn=lambda: shutil.which("vigia-log") is not None,
    ),
    ToolEntry(
        id="privacy-controls",
        name="Privacy Controls",
        description="Painel central de toggles de privacidade (localizacao, "
        "telemetria, lock screen, firewall, SSH, Tor, etc.).",
        icon="br.com.vigia.PrivacyControls",
        exec_cmd=["vigia-privacy"],
        needs_terminal=False,
        available_fn=lambda: shutil.which("vigia-privacy") is not None,
    ),
]
