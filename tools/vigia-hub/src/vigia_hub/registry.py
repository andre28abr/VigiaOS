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


# Categorias para agrupamento visual na sidebar.
# Ordem aqui define ordem de exibicao.
CATEGORIES_ORDER = [
    "monitoramento",
    "privacidade",
    "defesa",
    "relatorios",
]

CATEGORY_LABELS = {
    "monitoramento": "Monitoramento",
    "privacidade": "Privacidade",
    "defesa": "Defesa & Hardening",
    "relatorios": "Relatorios",
}


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
    # Modulo Python que exporta build_content() -> Gtk.Widget.
    # Quando nao-None E disponivel, o Hub embarca o widget direto no
    # painel direito em vez de abrir a tool via subprocess.
    embedded_module: str | None = None
    # Categoria para agrupamento visual na sidebar (chave de CATEGORY_LABELS).
    # Default "monitoramento" se nao especificado.
    category: str = "monitoramento"
    # Pacote(s) original(is) que esta tool "wrappa" (ex: ["lynis"]).
    # Mostrado como badge no header pra dar transparencia ao user.
    wrapped_packages: list[str] = field(default_factory=list)

    def is_available(self) -> bool:
        try:
            return self.available_fn()
        except Exception:
            return False

    def is_embeddable(self) -> bool:
        """Pode ser embarcada no Hub (vs. abrir externa)?"""
        return self.embedded_module is not None and self.is_available()


def tools_by_category(tools: list[ToolEntry]) -> dict[str, list[ToolEntry]]:
    """Agrupa tools por categoria respeitando CATEGORIES_ORDER."""
    grouped: dict[str, list[ToolEntry]] = {}
    for t in tools:
        grouped.setdefault(t.category, []).append(t)
    return {c: grouped[c] for c in CATEGORIES_ORDER if c in grouped}


# ============================================================================
# Tools registry
# ============================================================================

TOOLS: list[ToolEntry] = [
    ToolEntry(
        id="activity-log",
        name="Activity Log",
        description="Visualizador de logs do sistema com narrativa human-readable.",
        long_description=(
            "Frontend **GTK4** do `vigia-log` (parser Rust). Consolida `audit.log`, "
            "`systemd journal` e `fail2ban.log` numa **unica linha do tempo**, "
            "traduzidos do formato cru para frases em portugues que dizem *o que "
            "aconteceu*, *quem fez*, *quando* e *por que e' notavel*.\n\n"
            "Detecta **correlations** cross-source — *fail2ban baniu 192.0.2.42 "
            "apos 3 tentativas SSH em 10s*, *Sistema OOM killed chromium*, "
            "*SELinux bloqueou httpd multiplas vezes em 60s*. O **severity "
            "classifier** reduz ruido em ate 98% num `audit.log` tipico.\n\n"
            "Arquitetura: o parser Rust (`vigia-log --output json-bundle`) faz "
            "todo trabalho pesado e cospe JSON; este GUI Python apenas renderiza. "
            "**Modo admin** opt-in via `pkexec` (1 dialog) habilita audit + "
            "journal do sistema + fail2ban."
        ),
        features=[
            "**3 tabs**: Status (KPIs), Timeline (eventos), Correlations",
            "Multi-source: `audit` + `journald` + `fail2ban` interleavados por timestamp",
            "4 patterns de correlation cross-source (`fail2ban_burst`, `oom_kill`, `selinux_burst`, `ssh_suspeito`)",
            "Classificador automatico: **routine** / **interesting** / **suspicious**",
            "Engine Rust mantida — performance preservada em logs grandes",
        ],
        icon_path=_TOOLS_DIR / "activity-log-gui" / "data" / "br.com.vigia.ActivityLog.svg",
        exec_cmd=["vigia-log-gui"],
        needs_terminal=False,
        needs_root=False,
        available_fn=lambda: shutil.which("vigia-log-gui") is not None and shutil.which("vigia-log") is not None,
        embedded_module="vigia_log_gui.window",
        category="monitoramento",
        wrapped_packages=["vigia-log", "audit", "fail2ban"],
    ),
    ToolEntry(
        id="privacy-controls",
        name="Privacy Controls",
        description="Painel central de toggles de privacidade.",
        long_description=(
            "Centraliza **13 configuracoes de privacidade** do GNOME e do sistema "
            "que normalmente exigem editar `dconf`, `/etc/selinux/config`, "
            "`systemctl` ou `firewall-cmd` separadamente. Cada toggle muda o "
            "estado **real** do sistema na hora.\n\n"
            "**User-scope** (sem senha): localizacao, telemetria GNOME, historico "
            "de arquivos recentes, uso de apps, identidade em arquivos, "
            "lock screen automatico, previa de notificacoes na lock, limpeza "
            "automatica de lixeira/temp, Bluetooth.\n\n"
            "**System-scope** (pede senha admin via polkit): firewall on/off, "
            "servidor SSH, servico Tor."
        ),
        features=[
            "**10 toggles user-scope** via `dconf` (sem senha)",
            "**3 toggles system-scope** via `pkexec` (firewall, SSH, Tor)",
            "Toggle indisponivel detectado e exibido *dimmed* (ex: bluetooth sem adapter)",
            "Mudancas sincronizadas com **GNOME Settings** em tempo real",
        ],
        icon_path=_TOOLS_DIR
        / "privacy-controls"
        / "data"
        / "br.com.vigia.PrivacyControls.svg",
        exec_cmd=["vigia-privacy"],
        needs_terminal=False,
        available_fn=lambda: shutil.which("vigia-privacy") is not None,
        embedded_module="vigia_privacy.window",
        category="privacidade",
        wrapped_packages=["dconf", "systemctl"],
    ),
    ToolEntry(
        id="vpn-manager",
        name="VPN Manager",
        description="Gerenciador WireGuard com UI grafica.",
        long_description=(
            "Gerencia conexoes **WireGuard** com UI grafica. Lista perfis "
            "em `/etc/wireguard/*.conf`, conecta/desconecta com 1 clique e "
            "mostra status detalhado dos peers (handshake, dados "
            "transferidos, endpoints).\n\n"
            "Substitui o passo-a-passo manual no terminal "
            "(`sudo wg-quick up <perfil>`, `sudo wg show <iface>`). Cada "
            "operacao usa **1 dialog `pkexec`** — sem precisar abrir terminal.\n\n"
            "Suporta **importar** novo perfil colando o conteudo do `.conf` "
            "(recebido do servidor VPN ou provedor como Mullvad, ProtonVPN). "
            "Vigia instala em `/etc/wireguard/` com permissions corretas "
            "(`0700` no diretorio, `0600` no arquivo).\n\n"
            "OpenVPN vira em **v0.2**. Por agora, foco em WireGuard que e' "
            "o estado-da-arte (kernel module, criptografia moderna, config "
            "simples)."
        ),
        features=[
            "**3 tabs**: Status (hero card + peers), Perfis (CRUD), Sobre",
            "Connect/Disconnect via `pkexec wg-quick up/down` (1 dialog cada)",
            "Importacao de `.conf` via dialog (paste do conteudo)",
            "Status detalhado: peers, handshake, rx/tx bytes, allowed IPs",
            "Listing inicial de perfis via `pkexec` (1 dialog cobre todos)",
        ],
        icon_path=_TOOLS_DIR / "vpn-manager" / "data" / "br.com.vigia.VpnManager.svg",
        exec_cmd=["vigia-vpn"],
        needs_terminal=False,
        available_fn=lambda: shutil.which("vigia-vpn") is not None,
        embedded_module="vigia_vpn.window",
        category="privacidade",
        wrapped_packages=["wireguard-tools", "wg-quick"],
    ),
    ToolEntry(
        id="selinux-gui",
        name="SELinux Manager",
        description="Gerenciador GTK4 moderno para SELinux.",
        long_description=(
            "Substituto visual do `system-config-selinux` antigo (GTK2). "
            "**6 tabs** cobrindo as operacoes essenciais:\n\n"
            "**Status**: modo *runtime* + modo *persistente* (edita "
            "`/etc/selinux/config`), policy carregada, versao.\n\n"
            "**Booleans**: ~300 booleans com descricoes em portugues; search "
            "por nome **OU** descricao.\n\n"
            "**Denials**: AVC blocks recentes via `ausearch` + botao *Gerar* "
            "que roda `audit2allow` e sugere o policy module.\n\n"
            "**Files**: `restorecon` por path — resolve 90% dos 'movi arquivo "
            "e parou de funcionar'.\n\n"
            "**Network** e **Processes**: read-only, mostram port mappings "
            "(`semanage port -l`) e contextos de processos rodando (`ps -eZ`)."
        ),
        features=[
            "**60+ descricoes pt-BR** escritas para os booleans mais comuns",
            "`audit2allow` integrado: clique *Gerar* apos selecionar um denial",
            "Persistent mode toggle (edita `/etc/selinux/config` via `pkexec`)",
            "Disabled warning visivel quando SELinux desligado",
            "Cores semanticas: *Enforcing* verde, *Permissive* ambar, *Disabled* vermelho",
        ],
        icon_path=_TOOLS_DIR / "selinux-gui" / "data" / "br.com.vigia.SelinuxGui.svg",
        exec_cmd=["vigia-selinux"],
        needs_terminal=False,
        available_fn=lambda: shutil.which("vigia-selinux") is not None,
        embedded_module="vigia_selinux.window",
        category="defesa",
        wrapped_packages=["semanage", "setsebool"],
    ),
    ToolEntry(
        id="firewall-gui",
        name="Firewall Manager",
        description="Gerenciador GTK4 para firewalld (zonas, services, portas).",
        long_description=(
            "Wrapper grafico de `firewall-cmd` que substitui o `firewall-config` "
            "antigo. Pensado para o **dia-a-dia**: ligar/desligar daemon, mudar "
            "zona padrao, e gerenciar quais services e portas estao abertos "
            "em cada zona.\n\n"
            "Mudancas escrevem `--permanent` + `--reload` (persistem no boot "
            "**E** aplicam imediatamente). Sem necessidade de lembrar dos "
            "comandos cheios de flags."
        ),
        features=[
            "**Status**: daemon active/inactive com botao *Start/Stop*",
            "**Zona padrao**: combo dropdown via `--set-default-zone`",
            "**Zonas ativas**: lista zona → interfaces/sources",
            "**CRUD de services** por zona (combo com os pre-definidos disponiveis)",
            "**CRUD de portas** customizadas (TCP/UDP, single ou range)",
        ],
        icon_path=_TOOLS_DIR / "firewall-gui" / "data" / "br.com.vigia.FirewallGui.svg",
        exec_cmd=["vigia-firewall"],
        needs_terminal=False,
        available_fn=lambda: shutil.which("vigia-firewall") is not None,
        embedded_module="vigia_firewall.window",
        category="defesa",
        wrapped_packages=["firewall-cmd"],
    ),
    ToolEntry(
        id="netmon-gui",
        name="Network Monitor",
        description="Conexoes TCP/UDP em tempo real (quem fala com quem).",
        long_description=(
            "Visualizador grafico de `ss -tunap` com **auto-refresh**. Lista "
            "TODAS as conexoes ativas (TCP + UDP, qualquer estado), com nome "
            "do processo e PID. Tab **Listening** separada mostra apenas "
            "servidores ativos no host — critico para saber *o que esta "
            "exposto*.\n\n"
            "**Modo admin** opt-in via `pkexec` revela nomes de processos do "
            "sistema (`systemd-resolve`, `NetworkManager`, `cupsd`, etc.) que "
            "normalmente ficariam como *(processo restrito)* quando rodando "
            "como user."
        ),
        features=[
            "**Auto-refresh** a cada 3s (toggleavel)",
            "Search filtra por *processo*, *IP* ou *porta*",
            "State badge colorido (*ESTAB* verde, *LISTEN* accent, *WAIT* ambar)",
            "Tab **Listening**: so servidores ativos no host",
            "**Modo admin** via `pkexec`: nomes de processos do sistema",
        ],
        icon_path=_TOOLS_DIR / "netmon-gui" / "data" / "br.com.vigia.NetMon.svg",
        exec_cmd=["vigia-netmon"],
        needs_terminal=False,
        available_fn=lambda: shutil.which("vigia-netmon") is not None,
        embedded_module="vigia_netmon.window",
        category="monitoramento",
        wrapped_packages=["ss"],
    ),
    ToolEntry(
        id="hardening-checks",
        name="Hardening Checks",
        description="Auditoria de hardening do sistema (wrapper Lynis).",
        long_description=(
            "Roda o **Lynis** (~250 controles de seguranca) e mostra o resultado "
            "numa interface escaneavel em vez do wall-of-text padrao do terminal. "
            "O **Hardening Index** (0–100) e' a metrica principal — quanto maior, "
            "melhor a postura geral.\n\n"
            "Os achados sao divididos em duas categorias:\n\n"
            "- **Warnings** — problemas que merecem atencao imediata (ex: "
            "*senha de root nao configurada para single user mode*).\n"
            "- **Suggestions** — melhorias incrementais (ex: *habilitar AIDE "
            "para integridade de arquivos*).\n\n"
            "Cada finding tem um `test-id` (ex: `KRNL-5820`) que pode ser "
            "googled para entender o contexto e ver a remediation oficial do "
            "Lynis. Util para **demonstrar postura LGPD** num escritorio de "
            "advocacia."
        ),
        features=[
            "**Hardening Index** colorido (verde / ambar / vermelho)",
            "Botao *Executar* dispara `lynis audit system` via `pkexec`",
            "Warnings e suggestions com **busca + filtro por categoria**",
            "Visao agregada por categoria (`AUTH`, `BOOT`, `KRNL`, `MACF`, etc.) com labels pt-BR",
            "Parser de `/var/log/lynis-report.dat` (carrega audit anterior automaticamente)",
        ],
        icon_path=_TOOLS_DIR / "hardening-checks" / "data" / "br.com.vigia.HardeningChecks.svg",
        exec_cmd=["vigia-hardening"],
        needs_terminal=False,
        available_fn=lambda: shutil.which("vigia-hardening") is not None,
        embedded_module="vigia_hardening.window",
        category="defesa",
        wrapped_packages=["lynis"],
    ),
    ToolEntry(
        id="reports",
        name="Reports",
        description="Gera relatorios HTML/PDF a partir de logs do sistema.",
        long_description=(
            "Consolida eventos do `journalctl` (**SSH**, **sudo**, **pkexec**, "
            "**fail2ban**) e do `last`/`lastb` em **relatorios HTML** prontos "
            "para impressao em PDF via Firefox/Chromium. Templates pre-definidos "
            "com **paleta zinc + emerald** e layout pensado para auditoria.\n\n"
            "Cada relatorio inclui KPIs no topo (cards com numero grande) seguido "
            "de tabelas detalhadas. Util para *reviews mensais*, *compliance "
            "LGPD* e *resposta a incidentes*.\n\n"
            "Os HTMLs sao salvos em `~/Documents/VigiaReports/` e listados na aba "
            "**Biblioteca** com botoes *Abrir* e *Excluir*. **Modo admin** "
            "opt-in via `pkexec` revela dados do journal do sistema e historico "
            "de logins falhados (`lastb` precisa de root)."
        ),
        features=[
            "**2 templates** v0.1: *atividade geral* + *eventos de autenticacao*",
            "KPI cards + tabelas detalhadas com tags coloridas (*aceito*, *falha*)",
            "Paleta visual identica ao restante da suite (zinc + emerald)",
            "Auto-abre no navegador apos gerar — `Ctrl+P` para PDF",
            "Biblioteca lista relatorios salvos com **Abrir** / **Excluir**",
        ],
        icon_path=_TOOLS_DIR / "reports" / "data" / "br.com.vigia.Reports.svg",
        exec_cmd=["vigia-reports"],
        needs_terminal=False,
        available_fn=lambda: shutil.which("vigia-reports") is not None,
        embedded_module="vigia_reports.window",
        category="relatorios",
        wrapped_packages=["journalctl", "last"],
    ),
    ToolEntry(
        id="file-integrity",
        name="File Integrity",
        description="Monitor de integridade de arquivos (wrapper AIDE).",
        long_description=(
            "Wrapper grafico do **AIDE** (Advanced Intrusion Detection "
            "Environment). Cria um *snapshot* dos arquivos do sistema "
            "(`hash SHA256`, permissoes, mtime, size, owner) e compara o "
            "estado atual com esse **baseline** sempre que voce roda "
            "*Verificar*.\n\n"
            "Mostra resultado de forma escaneavel: **Integro** (verde) "
            "quando nada mudou, **Mudancas detectadas** (ambar) quando ha "
            "diferenca. A aba *Mudancas* lista cada arquivo com badge "
            "colorido (*adicionado* / *removido* / *modificado*) e as "
            "propriedades alteradas (mtime, hash, permissoes, etc.).\n\n"
            "**Re-baseline** explicito apos updates legitimos do sistema "
            "(`rpm-ostree upgrade`), com dialog de confirmacao para evitar "
            "aceitar mudancas suspeitas por engano. Cada operacao usa "
            "**1 dialog `pkexec`** — sem repetir senha."
        ),
        features=[
            "**Hero card** com estado atual: integro / mudancas detectadas / sem baseline",
            "Lista filtravel de mudancas com badges (*adicionado*, *removido*, *modificado*)",
            "Cada mudanca mostra **propriedades alteradas** (mtime, hash, perms, etc.)",
            "Dialog de confirmacao explicito antes de re-baseline (evita aceitar mudancas suspeitas)",
            "Cache local em `~/.config/vigia/file-integrity.json` (mostra ultimo check apos restart)",
        ],
        icon_path=_TOOLS_DIR / "file-integrity" / "data" / "br.com.vigia.FileIntegrity.svg",
        exec_cmd=["vigia-integrity"],
        needs_terminal=False,
        available_fn=lambda: shutil.which("vigia-integrity") is not None,
        embedded_module="vigia_integrity.window",
        category="defesa",
        wrapped_packages=["aide"],
    ),
    # NOTA: Tool Installer NAO esta mais nesta lista. Foi promovido a
    # entidade de primeiro nivel acessivel via icone 'Instalador' na
    # nav lateral fina do Hub (em vez de virar mais uma tool entre tools).
    # Definicao continua em tools/tool-installer/ e e' importado pela
    # window.py do Hub.
]
