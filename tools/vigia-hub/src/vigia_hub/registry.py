"""Registry das ferramentas da Vigia Suite.

Para adicionar uma ferramenta nova: cria uma `ToolEntry` e adiciona em `TOOLS`.
Ordem na lista controla ordem visual no hub.

Cada tool sabe se precisa de terminal (CLI) ou roda direto (GUI), e se precisa
de root (entao prefix com sudo).

Icons sao resolvidos por caminho de arquivo absoluto (calculado relativo ao
modulo) em vez de icon-name do tema. Isso evita problemas com icon cache
nao atualizado e funciona out-of-the-box em modo editable (`pip install -e .`).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


# Resolve o repo root a partir da localizacao deste arquivo.
# Estrutura esperada: <repo>/tools/vigia-hub/src/vigia_hub/registry.py
# parents[4] = repo root
_REPO_ROOT = Path(__file__).resolve().parents[4]
_TOOLS_DIR = _REPO_ROOT / "tools"


@dataclass
class ToolEntry:
    id: str
    name: str
    description: str
    icon_path: Path  # caminho absoluto do SVG
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
        icon_path=_REPO_ROOT / "packaging" / "vigia-log.svg",
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
        icon_path=_TOOLS_DIR
        / "privacy-controls"
        / "data"
        / "br.com.vigia.PrivacyControls.svg",
        exec_cmd=["vigia-privacy"],
        needs_terminal=False,
        available_fn=lambda: shutil.which("vigia-privacy") is not None,
    ),
    ToolEntry(
        id="selinux-gui",
        name="SELinux Manager",
        description="Gerenciador GTK4 para SELinux: muda modo "
        "(Enforcing/Permissive) e gerencia booleans com search.",
        icon_path=_TOOLS_DIR / "selinux-gui" / "data" / "br.com.vigia.SelinuxGui.svg",
        exec_cmd=["vigia-selinux"],
        needs_terminal=False,
        available_fn=lambda: shutil.which("vigia-selinux") is not None,
    ),
    ToolEntry(
        id="firewall-gui",
        name="Firewall Manager",
        description="Gerenciador GTK4 para firewalld: zonas, services e portas. "
        "Substitui o firewall-config antigo.",
        icon_path=_TOOLS_DIR / "firewall-gui" / "data" / "br.com.vigia.FirewallGui.svg",
        exec_cmd=["vigia-firewall"],
        needs_terminal=False,
        available_fn=lambda: shutil.which("vigia-firewall") is not None,
    ),
    ToolEntry(
        id="netmon-gui",
        name="Network Monitor",
        description="Visualizador em tempo real de conexoes TCP/UDP. Lista quem "
        "esta falando com quem, com auto-refresh e filtros.",
        icon_path=_TOOLS_DIR / "netmon-gui" / "data" / "br.com.vigia.NetMon.svg",
        exec_cmd=["vigia-netmon"],
        needs_terminal=False,
        available_fn=lambda: shutil.which("vigia-netmon") is not None,
    ),
]
