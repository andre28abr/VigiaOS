"""Registry das ferramentas da Vigia Suite.

Para adicionar uma ferramenta nova: cria uma `ToolEntry` e adiciona em `TOOLS`.
Ordem na lista controla ordem visual no hub.

Icons sao resolvidos por caminho de arquivo absoluto (calculado relativo ao
modulo) em vez de icon-name do tema.

Cada ToolEntry tem:
- description: 1 linha curta (mostrada na sidebar/lista)
- long_description: paragrafos detalhados (mostrados no painel de detalhe)
- features: lista de bullet points com features principais
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


_REPO_ROOT = Path(__file__).resolve().parents[4]
_TOOLS_DIR = _REPO_ROOT / "tools"


@dataclass
class ToolEntry:
    id: str
    name: str
    description: str               # 1 linha para sidebar
    icon_path: Path
    exec_cmd: list[str]
    needs_terminal: bool = False
    needs_root: bool = False
    long_description: str = ""     # paragrafos para painel detalhe
    features: list[str] = field(default_factory=list)
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
        description="Visualizador de logs do sistema com narrativa human-readable.",
        long_description=(
            "Parser inteligente de logs do Linux: audit.log, systemd journal e "
            "fail2ban.log sao consolidados numa unica linha do tempo, traduzidos "
            "do formato cru para frases em portugues que dizem o que aconteceu, "
            "quem fez, quando e por que e' notavel.\n\n"
            "Alem de visualizar, detecta correlations entre fontes: 'fail2ban "
            "baniu 192.0.2.42 apos 3 tentativas SSH em 10s', 'Sistema OOM killed "
            "chromium', 'SELinux bloqueou httpd_t multiplas vezes em 60s'. "
            "Severity classifier reduz ruido em 98% num audit.log tipico."
        ),
        features=[
            "Multi-source: audit + journald + fail2ban interleavados por timestamp",
            "4 patterns de correlation cross-source (fail2ban_burst, oom_kill, selinux_burst, ssh_suspeito)",
            "Classificador automatico: routine / interesting / suspicious",
            "Live tail mode (-f) com refresh 2s",
            "TUI Ratatui com paleta zinc + emerald, filtros, search incremental",
        ],
        icon_path=_REPO_ROOT / "packaging" / "vigia-log.svg",
        exec_cmd=["vigia-log", "--sources", "audit", "journald", "fail2ban"],
        needs_terminal=True,
        needs_root=True,
        available_fn=lambda: shutil.which("vigia-log") is not None,
    ),
    ToolEntry(
        id="privacy-controls",
        name="Privacy Controls",
        description="Painel central de toggles de privacidade.",
        long_description=(
            "Centraliza 13 configuracoes de privacidade do GNOME e do sistema "
            "que normalmente exigem editar dconf, /etc/selinux/config, systemctl "
            "ou firewall-cmd separadamente. Cada toggle muda o estado real do "
            "sistema na hora.\n\n"
            "User-scope (sem senha): localizacao, telemetria GNOME, historico "
            "de arquivos recentes, uso de apps, identidade em arquivos, "
            "lock screen automatico, previa de notificacoes na lock, limpeza "
            "automatica de lixeira/temp, Bluetooth.\n\n"
            "System-scope (pede senha admin via polkit): firewall (on/off), "
            "servidor SSH, servico Tor."
        ),
        features=[
            "10 toggles user-scope via dconf (sem senha)",
            "3 toggles system-scope via pkexec (firewall, SSH, Tor)",
            "Toggle indisponivel detectado e exibido dimmed (ex: bluetooth sem adapter)",
            "Mudancas sincronizadas com GNOME Settings em tempo real",
        ],
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
        description="Gerenciador GTK4 moderno para SELinux.",
        long_description=(
            "Substituto visual do system-config-selinux antigo (GTK2). "
            "6 tabs cobrindo as operacoes essenciais:\n\n"
            "• Status: modo runtime + modo persistente (edita /etc/selinux/config), "
            "policy carregada, versao\n"
            "• Booleans: ~300 booleans com descricoes em portugues, search por "
            "nome ou descricao\n"
            "• Denials: AVC blocks recentes via ausearch + botao 'Gerar' audit2allow\n"
            "• Files: restorecon por path (resolve 'movi arquivo e parou de funcionar')\n"
            "• Network: port mappings (qual contexto possui qual porta)\n"
            "• Processes: contexto SELinux de processos rodando"
        ),
        features=[
            "60+ descricoes pt-BR escritas para os booleans mais comuns",
            "audit2allow integrado: clique 'Gerar' apos selecionar um denial",
            "Persistent mode toggle (edita /etc/selinux/config via pkexec)",
            "Disabled warning visivel quando SELinux desligado",
            "Cores semanticas: Enforcing verde, Permissive ambar, Disabled vermelho",
        ],
        icon_path=_TOOLS_DIR / "selinux-gui" / "data" / "br.com.vigia.SelinuxGui.svg",
        exec_cmd=["vigia-selinux"],
        needs_terminal=False,
        available_fn=lambda: shutil.which("vigia-selinux") is not None,
    ),
    ToolEntry(
        id="firewall-gui",
        name="Firewall Manager",
        description="Gerenciador GTK4 para firewalld (zonas, services, portas).",
        long_description=(
            "Wrapper grafico de firewall-cmd que substitui o firewall-config "
            "antigo. Pensado para o dia-a-dia: ligar/desligar daemon, mudar "
            "zona padrao, e gerenciar quais services e portas estao abertos "
            "em cada zona.\n\n"
            "Mudancas escrevem --permanent + --reload (persistem no boot E "
            "aplicam imediatamente). Sem necessidade de lembrar dos comandos."
        ),
        features=[
            "Status: daemon active/inactive com botao Start/Stop",
            "Zona padrao: combo dropdown para mudar via --set-default-zone",
            "Zonas ativas: lista zona -> interfaces/sources",
            "CRUD de services por zona (combo com os pre-definidos disponiveis)",
            "CRUD de portas customizadas (TCP/UDP, single ou range)",
        ],
        icon_path=_TOOLS_DIR / "firewall-gui" / "data" / "br.com.vigia.FirewallGui.svg",
        exec_cmd=["vigia-firewall"],
        needs_terminal=False,
        available_fn=lambda: shutil.which("vigia-firewall") is not None,
    ),
    ToolEntry(
        id="netmon-gui",
        name="Network Monitor",
        description="Conexoes TCP/UDP em tempo real (quem fala com quem).",
        long_description=(
            "Visualizador grafico de 'ss -tunap' com auto-refresh. Lista TODAS "
            "as conexoes ativas (TCP + UDP, qualquer estado), com nome do "
            "processo e PID. Tab Listening separada mostra apenas servidores "
            "ativos no host (LISTEN ou UDP UNCONN com wildcard) — critico para "
            "saber 'o que esta exposto'.\n\n"
            "Modo admin opt-in via pkexec revela nomes de processos do sistema "
            "(systemd-resolve, NetworkManager, cupsd, etc.) que normalmente "
            "ficariam como '(processo restrito)' quando rodando como user."
        ),
        features=[
            "Auto-refresh a cada 3s (toggleavel)",
            "Search filtra por processo, IP, porta",
            "State badge colorido (ESTAB verde, LISTEN accent, WAIT ambar)",
            "Tab Listening: so servidores ativos no host",
            "Modo admin via pkexec: nomes de processos do sistema",
        ],
        icon_path=_TOOLS_DIR / "netmon-gui" / "data" / "br.com.vigia.NetMon.svg",
        exec_cmd=["vigia-netmon"],
        needs_terminal=False,
        available_fn=lambda: shutil.which("vigia-netmon") is not None,
    ),
]
