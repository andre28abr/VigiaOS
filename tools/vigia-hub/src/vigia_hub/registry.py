"""Registry das ferramentas do VigiaOS.

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

from vigia_common.platform import is_atomic


_REPO_ROOT = Path(__file__).resolve().parents[4]
_TOOLS_DIR = _REPO_ROOT / "tools"


# Categorias para agrupamento visual na sidebar.
# Ordem aqui define ordem de exibicao.
CATEGORIES_ORDER = [
    "monitoramento",
    "privacidade",
    "defesa",
    "sistema",
    "relatorios",
]

CATEGORY_LABELS = {
    "monitoramento": "Monitoramento",
    "privacidade": "Privacidade",
    "defesa": "Defesa & Hardening",
    "sistema": "Sistema",
    "relatorios": "Relatórios",
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
    # So' faz sentido em sistema atomico (rpm-ostree). Escondida no Hub
    # quando rodando em Fedora Workstation tradicional (ex: Deployments).
    atomic_only: bool = False

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


def visible_tools() -> list[ToolEntry]:
    """TOOLS aplicaveis a este sistema.

    Esconde tools `atomic_only` (ex: Deployments Manager) quando o sistema
    nao e' atomico (Fedora Workstation) — la' nao existe rpm-ostree nem
    deployments, entao a tool nao faria sentido.
    """
    atomic = is_atomic()
    return [t for t in TOOLS if atomic or not t.atomic_only]


# ============================================================================
# Tools registry
# ============================================================================

TOOLS: list[ToolEntry] = [
    ToolEntry(
        id="dashboard",
        name="Dashboard",
        description="Sistema em tempo real (CPU, RAM, disco, rede, processos).",
        long_description=(
            "Dashboard de sistema em tempo real — CPU, memória, disco I/O, "
            "rede e processos com gráficos via Cairo + GTK4. Substitui o uso "
            "de `htop`, `btop`, `glances`, `iotop` e `iftop` em uma UI "
            "nativa libadwaita.\n\n"
            "Dados vêm do `/proc` e `/sys` direto (kernel interface) — "
            "**sem subprocess** para a maioria das métricas, **sem deps "
            "externas pip**. Refresh 1Hz (CPU/RAM/Rede) e 2Hz (Processos).\n\n"
            "**Cores semânticas**: CPU em emerald, RAM em amber, Disco em "
            "ciano, Rede em violeta. Facilitar identificar de relance "
            "qual métrica está picando.\n\n"
            "**Kill de processos** com confirmação (SIGTERM ou SIGKILL). "
            "Processos de outros users requerem admin via pkexec.\n\n"
            "**Inspecionar processo**: botão por processo que roda "
            "`strace -c` por ~5s e mostra o resumo de syscalls (read-only, "
            "via pkexec). Só aparece se o `strace` estiver instalado — útil "
            "pra investigar o que um processo suspeito está fazendo."
        ),
        features=[
            "**5 tabs**: Visão Geral, Recursos, Processos, Alertas, Sobre",
            "Sparklines de CPU, RAM, RX/TX (60s de histórico)",
            "Gráficos Cairo: CPU por core + StackedBar de RAM + linha de Disco/Rede",
            "Temperatura via `/sys/class/thermal` (sem deps externas)",
            "Top 30 processos com filtros (search, sort, 'só meus')",
            "Kill com confirmação + pkexec para processos do sistema",
            "**Inspecionar** syscalls de um processo via `strace -c` (opcional, pkexec)",
            "**Sem persistencia** em disco — dados somem ao fechar",
        ],
        icon_path=_TOOLS_DIR / "dashboard" / "data" / "br.com.vigia.Dashboard.svg",
        exec_cmd=["vigia-dashboard"],
        needs_terminal=False,
        available_fn=lambda: shutil.which("vigia-dashboard") is not None,
        embedded_module="vigia_dashboard.window",
        category="monitoramento",
        wrapped_packages=["procfs", "strace"],
    ),
    ToolEntry(
        id="activity-log",
        name="Activity Log",
        description="Visualizador de logs do sistema com narrativa human-readable.",
        long_description=(
            "Frontend **GTK4** do `vigia-log` (parser Rust). Consolida `audit.log`, "
            "`systemd journal` e `fail2ban.log` numa **única linha do tempo**, "
            "traduzidos do formato cru para frases em português que dizem *o que "
            "aconteceu*, *quem fez*, *quando* e *por que é notável*.\n\n"
            "Detecta **correlations** cross-source — *fail2ban baniu 192.0.2.42 "
            "após 3 tentativas SSH em 10s*, *Sistema OOM killed chromium*, "
            "*SELinux bloqueou httpd múltiplas vezes em 60s*. O **severity "
            "classifier** reduz ruído em até 98% num `audit.log` típico.\n\n"
            "Arquitetura: o parser Rust (`vigia-log --output json-bundle`) faz "
            "todo trabalho pesado e cospe JSON; este GUI Python apenas renderiza. "
            "**Modo admin** opt-in via `pkexec` (1 dialog) habilita audit + "
            "journal do sistema + fail2ban."
        ),
        features=[
            "**4 tabs**: Status (KPIs), Timeline (eventos), Correlações, Sobre",
            "Multi-source: `audit` + `journald` + `fail2ban` interleavados por timestamp",
            "4 patterns de correlation cross-source (`fail2ban_burst`, `oom_kill`, `selinux_burst`, `ssh_suspeito`)",
            "Classificador automático: **routine** / **interesting** / **suspicious**",
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
            "Centraliza **13 configurações de privacidade** do GNOME e do sistema "
            "que normalmente exigem editar `dconf`, `/etc/selinux/config`, "
            "`systemctl` ou `firewall-cmd` separadamente. Cada toggle muda o "
            "estado **real** do sistema na hora.\n\n"
            "**User-scope** (sem senha): localização, telemetria GNOME, histórico "
            "de arquivos recentes, uso de apps, identidade em arquivos, "
            "lock screen automático, prévia de notificações na lock, limpeza "
            "automática de lixeira/temp, Bluetooth.\n\n"
            "**System-scope** (pede senha admin via polkit): firewall on/off, "
            "servidor SSH, serviço Tor."
        ),
        features=[
            "**10 toggles user-scope** via `dconf` (sem senha)",
            "**3 toggles system-scope** via `pkexec` (firewall, SSH, Tor)",
            "Toggle indisponível detectado e exibido *dimmed* (ex: bluetooth sem adapter)",
            "Mudanças sincronizadas com **GNOME Settings** em tempo real",
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
    # VPN Manager removida na limpeza 2026-05-27: NetworkManager nativo
    # do GNOME ja gerencia WireGuard out-of-the-box.
    ToolEntry(
        id="dns-manager",
        name="DNS Manager",
        description="Gerenciador DNS com provedores curados e DoT.",
        long_description=(
            "Gerencia o DNS do sistema via **systemd-resolved**. Catálogo de "
            "**9 provedores populares** (Cloudflare, Quad9, AdGuard, Mullvad, "
            "Google, etc.) com descrição + filtros (ads, malware, adulto) e "
            "**1-click apply**.\n\n"
            "**DNS over TLS (DoT)** encriptado por padrão — sem isso, ISP "
            "e qualquer um na sua rede vê seu histórico de navegação. "
            "Substitui o passo-a-passo manual em `/etc/systemd/resolved.conf` "
            "+ `systemctl restart`.\n\n"
            "**Backup automático** do config atual antes de aplicar — "
            "permite voltar com 1 botão. **Flush cache** quando precisar "
            "forçar nova resolução.\n\n"
            "Provedores com filtros (Cloudflare Family, AdGuard, Mullvad "
            "AdBlock) bloqueiam ads/malware/adulto no **nível DNS** — antes "
            "do navegador nem requisitar. Mais leve que ad-blocker no browser "
            "e funciona em todos os apps."
        ),
        features=[
            "**3 tabs**: Status (provedor + interfaces), Provedores (catálogo), Sobre",
            "Catálogo com **9 provedores curados** (Cloudflare, Quad9, AdGuard, Mullvad, ...)",
            "Toggle **DNS over TLS (DoT)** — encripta queries",
            "Backup automático do `/etc/systemd/resolved.conf` antes de aplicar",
            "**Flush cache** + **Restaurar padrão** com 1 clique",
        ],
        icon_path=_TOOLS_DIR / "dns-manager" / "data" / "br.com.vigia.DnsManager.svg",
        exec_cmd=["vigia-dns"],
        needs_terminal=False,
        available_fn=lambda: shutil.which("vigia-dns") is not None,
        embedded_module="vigia_dns.window",
        category="privacidade",
        wrapped_packages=["systemd-resolved", "resolvectl"],
    ),
    ToolEntry(
        id="selinux-gui",
        name="SELinux Manager",
        description="Gerenciador GTK4 moderno para SELinux.",
        long_description=(
            "Substituto visual do `system-config-selinux` antigo (GTK2). "
            "**6 tabs** cobrindo as operações essenciais:\n\n"
            "**Status**: modo *runtime* + modo *persistente* (edita "
            "`/etc/selinux/config`), policy carregada, versão.\n\n"
            "**Booleans**: ~300 booleans com descrições em português; search "
            "por nome **OU** descrição.\n\n"
            "**Denials**: AVC blocks recentes via `ausearch` + botão *Gerar* "
            "que roda `audit2allow` e sugere o policy module.\n\n"
            "**Files**: `restorecon` por path — resolve 90% dos 'movi arquivo "
            "e parou de funcionar'.\n\n"
            "**Network** e **Processes**: read-only, mostram port mappings "
            "(`semanage port -l`) e contextos de processos rodando (`ps -eZ`)."
        ),
        features=[
            "**60+ descrições pt-BR** escritas para os booleans mais comuns",
            "`audit2allow` integrado: clique *Gerar* após selecionar um denial",
            "Persistent mode toggle (edita `/etc/selinux/config` via `pkexec`)",
            "Disabled warning visível quando SELinux desligado",
            "Cores semânticas: *Enforcing* verde, *Permissive* âmbar, *Disabled* vermelho",
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
            "Wrapper gráfico de `firewall-cmd` que substitui o `firewall-config` "
            "antigo. Pensado para o **dia-a-dia**: ligar/desligar daemon, mudar "
            "zona padrão, e gerenciar quais services e portas estão abertos "
            "em cada zona.\n\n"
            "Mudanças escrevem `--permanent` + `--reload` (persistem no boot "
            "**E** aplicam imediatamente). Sem necessidade de lembrar dos "
            "comandos cheios de flags."
        ),
        features=[
            "**Status**: daemon active/inactive com botão *Start/Stop*",
            "**Zona padrão**: combo dropdown via `--set-default-zone`",
            "**Zonas ativas**: lista zona → interfaces/sources",
            "**CRUD de services** por zona (combo com os pré-definidos disponíveis)",
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
            "Visualizador gráfico de `ss -tunap` com **auto-refresh**. Lista "
            "TODAS as conexões ativas (TCP + UDP, qualquer estado), com nome "
            "do processo e PID. Tab **Listening** separada mostra apenas "
            "servidores ativos no host — crítico para saber *o que está "
            "exposto*.\n\n"
            "**Modo admin** opt-in via `pkexec` revela nomes de processos do "
            "sistema (`systemd-resolve`, `NetworkManager`, `cupsd`, etc.) que "
            "normalmente ficariam como *(processo restrito)* quando rodando "
            "como user."
        ),
        features=[
            "**Auto-refresh** a cada 3s (toggleável)",
            "Search filtra por *processo*, *IP* ou *porta*",
            "State badge colorido (*ESTAB* verde, *LISTEN* accent, *WAIT* âmbar)",
            "Tab **Listening**: só servidores ativos no host",
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
            "Roda o **Lynis** (~250 controles de segurança) e mostra o resultado "
            "numa interface escaneável em vez do wall-of-text padrão do terminal. "
            "O **Hardening Index** (0–100) é a métrica principal — quanto maior, "
            "melhor a postura geral.\n\n"
            "Os achados são divididos em duas categorias:\n\n"
            "- **Warnings** — problemas que merecem atenção imediata (ex: "
            "*senha de root não configurada para single user mode*).\n"
            "- **Suggestions** — melhorias incrementais (ex: *habilitar AIDE "
            "para integridade de arquivos*).\n\n"
            "Cada finding tem um `test-id` (ex: `KRNL-5820`) que pode ser "
            "googled para entender o contexto e ver a remediation oficial do "
            "Lynis. Útil para **demonstrar postura LGPD** num escritório de "
            "advocacia."
        ),
        features=[
            "**Hardening Index** colorido (verde / âmbar / vermelho)",
            "Botão *Executar* dispara `lynis audit system` via `pkexec`",
            "Warnings e suggestions com **busca + filtro por categoria**",
            "Visão agregada por categoria (`AUTH`, `BOOT`, `KRNL`, `MACF`, etc.) com labels pt-BR",
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
        description="Gera relatórios HTML/PDF a partir de logs do sistema.",
        long_description=(
            "Consolida eventos do `journalctl` (**SSH**, **sudo**, **pkexec**, "
            "**fail2ban**) e do `last`/`lastb` em **relatórios HTML** prontos "
            "para impressão em PDF via Firefox/Chromium. Templates pré-definidos "
            "com **paleta zinc + emerald** e layout pensado para auditoria.\n\n"
            "Cada relatório inclui KPIs no topo (cards com número grande) seguido "
            "de tabelas detalhadas. Útil para *reviews mensais*, *compliance "
            "LGPD* e *resposta a incidentes*.\n\n"
            "Os HTMLs são salvos em `~/.local/share/vigia-reports/` e listados na aba "
            "**Biblioteca** com botões *Abrir* e *Excluir*. **Modo admin** "
            "opt-in via `pkexec` revela dados do journal do sistema e histórico "
            "de logins falhados (`lastb` precisa de root)."
        ),
        features=[
            "**2 templates** v0.1: *atividade geral* + *eventos de autenticação*",
            "KPI cards + tabelas detalhadas com tags coloridas (*aceito*, *falha*)",
            "Paleta visual idêntica ao restante da suite (zinc + emerald)",
            "Auto-abre no navegador após gerar — `Ctrl+P` para PDF",
            "Biblioteca lista relatórios salvos com **Abrir** / **Excluir**",
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
        description="Integridade de arquivos: AIDE (sistema) + hash ad-hoc.",
        long_description=(
            "v0.2.0 unificou duas tools (File Integrity + Hash Tools). "
            "Cobre integridade em duas escalas:\n\n"
            "**Sistema (AIDE)**: snapshot completo de `/etc`, `/usr`, `/boot` "
            "com hash SHA256 + permissões + mtime + size + owner. Compara "
            "estado atual contra baseline pra detectar mudanças. Requer "
            "root via `pkexec`.\n\n"
            "**Ad-hoc (hash)**: calcula SHA-256/512/SHA-1/MD5 de arquivo "
            "individual, verifica hash conhecido vs computado, ou cria "
            "baseline JSON de diretório do user (Downloads, Documents) e "
            "faz diff sem root.\n\n"
            "**Use AIDE** pra audit periódico do sistema (semanal/mensal). "
            "**Use Hash ad-hoc** pra validar arquivos baixados ou snapshot "
            "de diretórios de trabalho."
        ),
        features=[
            "**6 tabs**: Status (AIDE), Mudanças (AIDE), Hash, Verificar, Baseline, Sobre",
            "**AIDE**: hero card íntegro/mudanças/sem baseline + lista filtrável de diffs",
            "**Hash ad-hoc**: 4 algoritmos (SHA-256, SHA-512, SHA-1, MD5)",
            "**Baseline ad-hoc**: snapshot JSON de diretório + diff added/modified/removed/**movido**",
            "Motor **hashdeep** opcional (mais rápido em pastas grandes; hash idêntico)",
            "Dialog de confirmação explícito antes de re-baseline AIDE",
            "Reports em `~/.config/vigia/file-integrity.json` + `~/.local/share/vigia-hash/`",
        ],
        icon_path=_TOOLS_DIR / "file-integrity" / "data" / "br.com.vigia.FileIntegrity.svg",
        exec_cmd=["vigia-integrity"],
        needs_terminal=False,
        available_fn=lambda: shutil.which("vigia-integrity") is not None,
        embedded_module="vigia_integrity.window",
        category="defesa",
        wrapped_packages=["aide", "coreutils", "hashdeep"],
    ),
    ToolEntry(
        id="capabilities-inspector",
        name="Capabilities Inspector",
        description="Auditoria de Linux capabilities (getcap).",
        long_description=(
            "Audita **Linux capabilities** no sistema. Capabilities são "
            "permissões granulares que substituem o 'tudo ou nada' do "
            "root — ex: `/usr/bin/ping` precisa apenas de `cap_net_raw` "
            "em vez de SUID root completo.\n\n"
            "Escaneia via `getcap -r` (1 dialog `pkexec` cobre todo o "
            "sistema). Lista cada binário com capabilities setadas, com "
            "**classificação de risco** ALTO/MÉDIO/BAIXO. **Vetor clássico "
            "de privilege escalation**: atacante adiciona `cap_setuid` em "
            "um binário inocuo e ganha root sem precisar de SUID.\n\n"
            "**Catálogo das ~40 capabilities** do kernel Linux como aba "
            "dedicada — descrição em pt-BR + classe de risco + contexto "
            "de uso comum. Útil pra entender o que cada cap permite "
            "exatamente.\n\n"
            "Read-only nesta v0.1 (não modifica capabilities). Modificação "
            "via UI chega na v0.2."
        ),
        features=[
            "**4 tabs**: Visão Geral, Binários, Capabilities (catálogo), Sobre",
            "Scan completo via `pkexec getcap -r /usr /opt /var` (1 dialog)",
            "Quick scan sem pkexec (paths user-readable)",
            "**40 capabilities catalogadas** pt-BR com classe de risco",
            "Filtros: por risco (ALTO/MÉDIO/BAIXO), search por path ou cap name",
        ],
        icon_path=_TOOLS_DIR / "capabilities-inspector" / "data" / "br.com.vigia.CapabilitiesInspector.svg",
        exec_cmd=["vigia-caps"],
        needs_terminal=False,
        available_fn=lambda: shutil.which("vigia-caps") is not None,
        embedded_module="vigia_caps.window",
        category="defesa",
        wrapped_packages=["libcap", "getcap"],
    ),
    ToolEntry(
        id="rootkit-scanner",
        name="Rootkit Scanner",
        description="Procura rootkits e backdoors (chkrootkit + rkhunter).",
        long_description=(
            "Wrappa **chkrootkit** e **Rootkit Hunter (rkhunter)** num só app "
            "com UI moderna. Os dois são scanners clássicos de Linux para "
            "detectar rootkits, backdoors e sinais de comprometimento.\n\n"
            "**chkrootkit**: rápido (~30s), faz checks específicos por "
            "binário (substituições de `ps`, `ls`, `netstat`, etc.). Bom "
            "como primeiro pente-fino.\n\n"
            "**rkhunter**: completo (2-5min), 200+ checks (hashes, "
            "permissões, configs SSH, processos escondidos). Mais detalhado.\n\n"
            "Os dois são complementares — rode periodicamente (ex: semanal) "
            "e cheque o Histórico pra mudanças suspeitas. Roda como root "
            "via `pkexec` em ambos."
        ),
        features=[
            "**4 tabs**: chkrootkit, Rootkit Hunter, Histórico, Sobre",
            "Streaming de output em tempo real (coloring warnings/infectados)",
            "KPI cards: testes rodados, warnings, infectados",
            "Botão Parar para cancelar scan a qualquer momento",
            "Histórico em `~/.local/share/vigia-rootkit/scans/` (mode 0600)",
            "Output completo salvo em JSON pra audit/LGPD",
        ],
        icon_path=_TOOLS_DIR / "rootkit-scanner" / "data" / "br.com.vigia.RootkitScanner.svg",
        exec_cmd=["vigia-rootkit"],
        needs_terminal=False,
        available_fn=lambda: shutil.which("vigia-rootkit") is not None,
        embedded_module="vigia_rootkit.window",
        category="defesa",
        wrapped_packages=["chkrootkit", "rkhunter"],
    ),
    ToolEntry(
        id="antivirus",
        name="Antivirus",
        description="Scan on-demand de malware com ClamAV.",
        long_description=(
            "Antivirus on-demand para Linux desktop usando o engine **ClamAV**. "
            "Escaneia arquivos e diretórios sob demanda, mantém a base de "
            "assinaturas atualizada (~250 MB) e mostra findings em UI moderna.\n\n"
            "Substitui o `clamtk` (UI envelhecida, problemas em GTK4) com "
            "interface nativa libadwaita. Streaming de progress durante scan, "
            "summary com contagens, histórico em JSON com permissões 0600.\n\n"
            "**Quando usar**: escanear downloads recebidos via email, validar "
            "arquivos antes de mandar pra clientes Windows, audit periódico "
            "para LGPD-compliance (logs são evidência de processo)."
        ),
        features=[
            "**3 tabs**: Scan (com banner inteligente), Base de dados, Sobre",
            "Streaming de findings em tempo real durante scan",
            "Update de base com 1 dialog `pkexec freshclam`",
            "Atalhos: Home, Downloads, Documents, /tmp",
            "Histórico em `~/.local/share/vigia-antivirus/` (mode 0600)",
            "Detecta daemon `clamd` (futuro: usar para scans mais rápidos)",
        ],
        icon_path=_TOOLS_DIR / "antivirus" / "data" / "br.com.vigia.Antivirus.svg",
        exec_cmd=["vigia-antivirus"],
        needs_terminal=False,
        available_fn=lambda: shutil.which("vigia-antivirus") is not None,
        embedded_module="vigia_antivirus.window",
        category="defesa",
        wrapped_packages=["clamav", "clamav-update"],
    ),
    # Network Scanner (nmap GUI) removida na limpeza 2026-05-27: fora do
    # escopo LGPD/escritorio + risco etico (scan nao-autorizado e' crime).
    # Firmware Analyzer (binwalk) removida na mesma limpeza: nicho de
    # reverse engineering/CTF, fora do escopo.
    # Hash Tools mergeada em 2026-05-27 → Vigia File Integrity v0.2.0.
    # As 3 tabs (Hash, Verificar, Baseline) viraram tabs do File Integrity
    # (que ja era escala-sistema com AIDE). Hash ad-hoc + AIDE = mesma
    # categoria de integridade de arquivos.
    ToolEntry(
        id="deployments-manager",
        name="Deployments Manager",
        description="Gerenciador de deployments rpm-ostree (boot snapshots).",
        long_description=(
            "GUI pra gerenciar os **deployments do rpm-ostree** — os "
            "'snapshots' que aparecem no menu do GRUB ao bootar.\n\n"
            "Cada deployment é um estado imutável do sistema, criado "
            "automaticamente em cada `rpm-ostree install/upgrade/rebase`. "
            "Você pode reverter pro anterior, pinnar pra preservar de "
            "cleanups automáticos, ou adicionar label/notas customizados "
            "pra documentar (LGPD/audit).\n\n"
            "**Cleanup integrado**: botão 'Limpar tudo' executa `rpm-ostree "
            "cleanup -p -r -m` num só pkexec — libera espaço em `/boot` "
            "(partição pequena: 600MB-1GB). Tool alerta quando `/boot` "
            "passa de 70% (amarelo) ou 85% (vermelho)."
        ),
        features=[
            "**3 tabs**: Deployments, Cleanup, Sobre",
            "Lista deployments com badges: ATIVO/STAGED/PIN/ROLLBACK",
            "Rollback pro deployment anterior via pkexec",
            "Pin/Unpin pra preservar contra cleanup automático",
            "Label customizado + notas multilinha por deployment",
            "Cleanup all em 1 click (`-p -r -m` num pkexec)",
            "Alerta visual de `/boot` cheio (>70% amarelo, >85% vermelho)",
            "State local em `~/.config/vigia-deployments/state.json` (mode 0600)",
        ],
        icon_path=_TOOLS_DIR / "deployments-manager" / "data" / "br.com.vigia.DeploymentsManager.svg",
        exec_cmd=["vigia-deployments"],
        needs_terminal=False,
        available_fn=lambda: shutil.which("vigia-deployments") is not None,
        embedded_module="vigia_deployments.window",
        category="sistema",
        wrapped_packages=["rpm-ostree"],
        atomic_only=True,
    ),
    # NOTA: Tool Installer NAO esta mais nesta lista. Foi promovido a
    # entidade de primeiro nivel acessivel via icone 'Instalador' na
    # nav lateral fina do Hub (em vez de virar mais uma tool entre tools).
    # Definicao continua em tools/tool-installer/ e e' importado pela
    # window.py do Hub.
]
