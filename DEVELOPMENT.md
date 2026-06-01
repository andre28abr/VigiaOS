# VigiaOS — Guia de Desenvolvimento (v2)

> **Documento vivo.** Atualizar a cada mudança significativa. Serve como
> contexto completo para retomar o desenvolvimento (humano ou IA) sem
> precisar reler histórico de PRs ou conversas anteriores.
>
> Última atualização: 2026-05-28 (revisão 5: +Hub v0.5.10 autostart/tray/lock, +Deployments Manager v0.1)

---

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Evolução: v1 → v2 → toolkit completo](#2-evolução-v1--v2--toolkit-completo)
3. [Decisões de arquitetura](#3-decisões-de-arquitetura)
4. [Estrutura do repositório](#4-estrutura-do-repositório)
5. [Catálogo de ferramentas — estado atual](#5-catálogo-de-ferramentas--estado-atual)
6. [Padrões e convenções comuns](#6-padrões-e-convenções-comuns)
7. [Como adicionar uma ferramenta nova](#7-como-adicionar-uma-ferramenta-nova)
8. [Setup numa máquina nova (Silverblue limpa)](#8-setup-numa-máquina-nova-silverblue-limpa)
9. [Log de implementação](#9-log-de-implementação)
10. [Roadmap](#10-roadmap)
11. [Lições aprendidas](#11-lições-aprendidas)
12. [Tags de restauração](#12-tags-de-restauração)
13. [Troubleshooting](#13-troubleshooting)
14. [Apêndice: comandos de referência rápida](#apêndice-comandos-de-referência-rápida)

---

## 1. Visão geral

**VigiaOS** é uma **suite de ferramentas** para Fedora Silverblue, focada em:

- **Segurança**: scan, audit, IDS, forensics
- **Privacidade**: toggles centrais, Tor Browser, DNS over TLS
- **LGPD/Compliance**: audit log + relatórios em PDF
- **Network insight**: monitor de conexões, VPN, DNS
- **Integridade**: AIDE, hardening checks (Lynis), capabilities audit
- **Descoberta**: catálogo curado de ferramentas de segurança via `rpm-ostree`

**NÃO** é uma distribuição Linux. Usa Silverblue **vanilla** e adiciona
software por cima (layered + flatpak).

**Alvo de hardware**: aarch64 e x86_64 (Apple Silicon via UTM + PCs).

**Contexto do autor**: André Augusto Azarias de Souza, dono do
**SentinelBR** (escritório de advocacia). Caso de uso primário é
**LGPD-compliance e segurança da informação para escritórios de
advocacia** — ambiente onde clientes confiam dados sensíveis e o
profissional precisa demonstrar diligência.

**Estado atual** (2026-05-28): **17 ferramentas focadas em LGPD/escritório**
integradas via Hub com layout master-detail-content (3 painéis) + categorias +
modo embedded. Limpeza 2026-05-27 removeu 3 tools fora do escopo (Network
Scanner, Firmware Analyzer, VPN Manager) e mergeou Hash Tools no File Integrity.
Em 2026-05-28 adicionada **Deployments Manager** (rpm-ostree GUI).

| # | Ferramenta | Versão | Stack | Status |
|---|---|---|---|---|
| 1 | **Vigia Hub** | v0.7.1 | Python + GTK4 + libadwaita | 🟢 3 painéis + autostart XDG + tray (quick actions, subprocess GTK3) + lock Polkit + Ajuda (manuais MD) |
| 2 | **Activity Log (core)** | v0.7.1 (Rust) | Rust + Ratatui + Crossterm | 🟢 3 sources + correlations + JsonBundle |
| 3 | **Activity Log (GUI)** | v0.1.0 | Python + GTK4 | 🟢 Frontend do core Rust via JSON |
| 4 | **Privacy Controls** | v0.3.1 | Python + GTK4 | 🟢 13 toggles user+system scope |
| 5 | **SELinux Manager** | v0.2.0 | Python + GTK4 | 🟢 6 tabs + pt-BR + audit2allow + lazy tabs |
| 6 | **Firewall Manager** | v0.1.0 | Python + GTK4 | 🟡 Status + zones CRUD |
| 7 | **Network Monitor** | v0.1.0 | Python + GTK4 | 🟡 Conexões + modo admin + auto-refresh smart |
| 8 | **Hardening Checks** | v0.1.4 | Python + GTK4 | 🟢 Lynis wrapper + perfil Silverblue |
| 9 | **Reports** | v0.1.1 | Python + GTK4 + Jinja2 + WeasyPrint | 🟢 PDF/HTML LGPD via Activity Log JSON |
| 10 | **File Integrity** | v0.2.1 | Python + GTK4 | 🟢 AIDE (sistema) + Hash ad-hoc (user) — 6 tabs |
| 11 | **Tool Installer** | v0.2.0 | Python + GTK4 | 🟢 Catálogo rpm-ostree + Extensoes navegador (FOSS) |
| 12 | **DNS Manager** | v0.4.1 | Python + GTK4 | 🟢 dnscrypt-proxy only — 11 servers curados |
| 13 | **Capabilities Inspector** | v0.1.0 | Python + GTK4 | 🟢 getcap audit + catálogo pt-BR de 41 caps |
| 14 | **Antivirus** | v0.1.1 | Python + GTK4 | 🟢 ClamAV wrapper — substitui clamtk |
| 15 | **Dashboard** | v0.2.1 | Python + GTK4 + Cairo | 🟢 Sistema em tempo real + per-process I/O + alertas |
| 16 | **Rootkit Scanner** | v0.2.0 | Python + GTK4 | 🟢 chkrootkit + rkhunter — pattern PreferencesGroup |
| 17 | **Deployments Manager** | v0.1.1 | Python + GTK4 | 🟢 rpm-ostree deployments (rollback/pin/cleanup) + labels/notas LGPD |

**Removidas na limpeza 2026-05-27** (foco LGPD/escritorio):
- ~~Network Scanner (nmap)~~ — fora do escopo + risco etico
- ~~Firmware Analyzer (binwalk)~~ — nicho reverse engineering/CTF
- ~~VPN Manager~~ — NetworkManager nativo do GNOME ja gerencia WireGuard
- ~~Hash Tools~~ — mergeado em File Integrity v0.2.0 (mesma categoria)

**Lib interna** (não conta como tool):
- **vigia-common** v0.1.0 — helpers compartilhados (make_clamp, show_error/info, md_to_pango, badges, constantes de layout). Reduz duplicação de ~600 linhas em 16 `_helpers.py`. Tools migradas via re-export retro-compatível.

---

## 2. Evolução: v1 → v2 → toolkit completo

### 2.1 v1 (BlueBuild distro) → v2 (toolkit) — pivot em 2026-05-22

A **v1** era uma distro completa buildada via BlueBuild — imagem container
publicada no GHCR, usuário rebasava com `rpm-ostree rebase`. Funcionava mas
trazia custos: manter pipeline de imagem (cosign, GHCR, runners ARM), brigar
com upstream Silverblue a cada release, e bug-surface próprio (theme, dconf,
GTK CSS — todos foram fontes de erros).

A **v2** elimina a imagem e foca no que diferencia: ferramentas próprias
rodando sobre Silverblue vanilla. A v1 está preservada em
[`legacy/v1-distro`](https://github.com/andre28abr/VigiaOS/tree/legacy/v1-distro)
para consulta.

### 2.2 Expansão do toolkit (2026-05-22 a 2026-05-25)

Iniciou com 6 ferramentas (Hub, Activity Log, Privacy, SELinux, Firewall,
NetMon). Expandiu para 19 ferramentas; depois enxugou para **16** (limpeza
2026-05-27 com foco LGPD). Ciclos principais:

| Ciclo | Adições | Foco |
|---|---|---|
| **Inicial** | Hub + 5 tools | Master-detail layout, fundação |
| **Compliance/audit** | Hardening Checks, Reports, File Integrity, Tool Installer, Activity Log GUI | LGPD + audit estendido |
| **Network/integrity** | VPN, DNS, Capabilities | Camada de rede privada + audit fino |
| **Security toolkit** | Antivirus, Network Scanner, Firmware Analyzer, Hash Tools | Análise prática (scan/RE/integrity) |
| **System monitoring** | Dashboard | Tempo real (CPU/RAM/disco/rede/processos) |

### 2.3 Refatorações de arquitetura

- **Embedded mode** (commit `c17e0b4`): todas tools exportam `build_content()
  -> Gtk.Widget`. Hub embarca direto no painel direito (single-window), com
  fallback para subprocess se não disponível.
- **Batch 1 performance** (commit `67b7e16`): async subprocess em 5 tools —
  `threading.Thread` worker + `GLib.idle_add` no UI thread. Resolveu
  travamentos de 1-3s ao abrir tools.
- **Batch 2 robustez** (commit `4a850e2`): 9 fixes em bugs latentes
  (race conditions em re-renders, exceptions silenciosas, timeouts curtos,
  detecção frágil de polkit cancel, etc.).
- **Silverblue tweaks** (commit `3bc9057`): perfil AIDE customizado (foco
  em `/etc`, `/root`, cron — pula `/usr` que é read-only), feedback Hardening
  com banners de contexto.
- **Layout redesign** (commit `2a8bde1`): 3 painéis (nav lateral fina com
  ícones + sidebar média com tools categorizadas + content), aba **Sobre**
  em todas as tools, `WRAPPED_PACKAGES` como sub-bar do header.
- **Polish v0.2** (commit `e5011e4`): AIDE exclui `/etc/systemd/system.control/`
  (false positives sistêmicos), VPN dialog com paste fallback (botão Colar +
  `grab_focus` inicial).
- **UI consistency pass** (commits `2cd8862`, `8198df1`, `e089e2f`,
  `0b72ba8`): 3 passes consecutivos baseados em feedback do user:
  - Remove `.pill` de 27 botões action (suggested/destructive) → forma
    retangular como o Reports
  - Padroniza espaçamentos em 26 arquivos: margens 24/32/28/28,
    header_lbl margin_bottom 8, header_desc 24, PreferencesGroup
    secundários ganham margin_top(24)
  - Tira botões de dentro dos cards do Hash Tools (Comparar, Criar
    baseline, Recarregar, Copiar) → Box própria com margin_top(16),
    halign=END. Spinners aparecem ANTES dos botões.
  - Antivirus v0.1.1: unifica Status+Scan → 3 tabs (era 4), banner
    inteligente no topo só aparece se há ação requerida.

---

## 3. Decisões de arquitetura

| Decisão | Escolha | Razão |
|---|---|---|
| **Base do sistema** | Fedora Silverblue vanilla | Red Hat mantém; sem fork; imagens atômicas robustas |
| **Distribuição** | `bootstrap.sh` + `pip install -e .` por tool | Sem image build; iteração local rápida |
| **Stack GUIs** | Python + PyGObject + GTK4 + libadwaita | Stack que o GNOME usa para apps oficiais; rápido de iterar |
| **Stack CLI perfance-críticas** | Rust 2021 + Ratatui + Crossterm | Activity Log core precisa parsear logs grandes; Rust para o motor, GTK para o frontend |
| **Privilege escalation** | `pkexec` opt-in via polkit | Dialog nativo do GNOME; cancelável; **NUNCA sudo** (regra fixa: feedback-pkexec-not-sudo) |
| **Pacotagem de comandos** | `pip install --user -e .` (editable) | Mudanças locais refletem sem reinstalar |
| **Bins acessíveis via sudo** | symlink em `/usr/local/bin/` (mutável no Silverblue) | sudo não vê `~/.local/bin/` por default |
| **Layout do Hub** | Master-detail-content (3 painéis) | Nav fina ícones → sidebar média categorizada → content rico |
| **Embedded mode** | `build_content() -> Gtk.Widget` por tool | Tools rodam no Hub OU standalone, mesma codebase |
| **Icons** | SVG 256x256, paleta zinc + emerald | Identidade visual consistente |
| **Entries .desktop** | `~/.local/share/applications/` (escopo user) | Não polui `/usr/share/` |
| **Identidade visual** | zinc-950 bg + emerald accent | Portada do app SentinelBR do autor |
| **WRAPPED_PACKAGES** | Sub-bar do header com label "Wrapper de:" + pills | Transparência: usuário vê qual pacote upstream a tool envolve |
| **Sobre tab** | Toda tool tem uma | "O que é + porque existe + comandos chamados + LGPD" |
| **Texto formatado** | Markdown leve (`**bold**`, `*italic*`, `` `code` ``) → Pango via `md_to_pango()` | Descrições longas ficam legíveis sem dependência pesada |
| **Defaults restritivos** | Firewall mínimo, services mínimos | Contexto LGPD/advocacia: abrir só o necessário (feedback-minimum-surface) |
| **LGPD permissions** | Reports/logs sensíveis → `chmod 0600` | Owner-only por padrão |

---

## 4. Estrutura do repositório

```
VigiaOS/
├── README.md                    # Pitch público
├── DEVELOPMENT.md               # Este arquivo (documento vivo)
├── LICENSE                      # Apache 2.0
├── .gitignore
│
├── bootstrap.sh                 # One-liner que prepara Silverblue vanilla
│
├── packaging/                   # Empacotamento RPM (preparado para COPR)
│   ├── vigia-activity-log.spec
│   ├── Makefile
│   ├── README.md                # Instruções de COPR
│   ├── vigia-log.desktop
│   └── vigia-log.svg
│
└── tools/                       # Uma pasta por ferramenta independente
    ├── activity-log/            # Rust — parser core (CLI/TUI/JSON)
    ├── activity-log-gui/        # Python — frontend GTK4 do core
    ├── vigia-hub/               # Python — launcher mestre (3 painéis)
    ├── privacy-controls/        # Python — 13 toggles
    ├── selinux-gui/             # Python — manager SELinux
    ├── firewall-gui/            # Python — manager firewalld
    ├── netmon-gui/              # Python — monitor de rede
    ├── hardening-checks/        # Python — wrapper Lynis
    ├── reports/                 # Python — PDF LGPD via Activity Log JSON
    ├── file-integrity/          # Python — wrapper AIDE
    ├── tool-installer/          # Python — catálogo rpm-ostree + extensões navegador
    ├── dns-manager/             # Python — wrapper dnscrypt-proxy (DoH/DoT)
    ├── capabilities-inspector/  # Python — getcap audit
    ├── antivirus/               # Python — wrapper ClamAV
    ├── dashboard/               # Python — sistema em tempo real (Cairo)
    └── rootkit-scanner/         # Python — chkrootkit + rkhunter
```

Cada ferramenta em `tools/` é um **projeto independente** com seu próprio
build system (`pyproject.toml`, `Cargo.toml`). Versionam separadamente.

---

## 5. Catálogo de ferramentas — estado atual

### 5.1 Vigia Hub (`tools/vigia-hub/`, v0.7.1)

**Função**: Launcher mestre. Um único ícone no menu GNOME que abre tudo.

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Layout (v0.5.0 — redesign)**: 3 painéis.

```
┌──────┬──────────────┬───────────────────────────────────┐
│ ICO  │  MONITORAMENTO│  [Sub-bar: Wrapper de: lynis]    │
│      │  • Activity   │  [Header da tool com tabs]       │
│ INST │  • NetMon     │                                   │
│  ⚙  │  PRIVACIDADE  │  [Conteudo embedded da tool]      │
│      │  • Privacy    │                                   │
│      │  • DNS        │                                   │
│      │  DEFESA       │                                   │
│      │  • Firewall   │                                   │
│      │  • SELinux    │                                   │
│      │  • Hardening  │                                   │
│      │  • File Integ.│                                   │
│      │  • Capabilities│                                  │
│      │  RELATORIOS   │                                   │
│      │  • Reports    │                                   │
└──────┴──────────────┴───────────────────────────────────┘
   ^             ^                      ^
   |             |                      |
nav fina    sidebar média          content rico
(ícones)    (categorizada)         (embedded ou detalhe)
```

**Categorias** (`registry.py`, 14 tools na sidebar):
- `monitoramento` — Dashboard, Activity Log, NetMon
- `privacidade` — Privacy Controls, DNS
- `defesa` — SELinux, Firewall, Hardening Checks, File Integrity, Capabilities, Rootkit Scanner, Antivirus
- `sistema` — Deployments Manager
- `relatorios` — Reports

**Tool Installer** (categoria à parte, ícone fixo na nav fina): aparece como
gear icon na nav lateral, não compete com tools de uso diário na sidebar.

**Componentes-chave**:
- `registry.py` — lista `TOOLS: list[ToolEntry]`. Para adicionar tool nova,
  basta 1 entry aqui (com `category`, `wrapped_packages`, `embedded_module`).
- `markdown.py` — conversor leve md → Pango markup (`**bold**`, `*italic*`,
  `` `code` ``)
- `window.py` — orquestra 3 painéis, `Adw.ViewStack` com 1 página por tool

**Embedded mode**: se a tool tem `embedded_module="vigia_X.embed"` e está
disponível, o Hub importa via `importlib.import_module()` + cache, e chama
`build_content() -> Gtk.Widget`. Caso contrário, subprocess launch.

**Sub-bar WRAPPED_PACKAGES**: `toolbar.add_top_bar()` com label
"Wrapper de:" + pills com nome do(s) pacote(s) original(is). Aparece abaixo
do header principal, antes do conteúdo da tool. Dá transparência ao
usuário sobre o que está sendo envolvido (ex: `lynis`, `aide`,
`dnscrypt-proxy`).

---

### 5.2 Vigia Activity Log — core (`tools/activity-log/`, v0.7.1 Rust)

**Função**: Parser de logs do Linux com narrativa human-readable.

**Stack**: Rust 2021 + Ratatui 0.29 + Crossterm 0.28 + Clap + Serde + Chrono.

**Sources suportadas**:
- `audit` (`/var/log/audit/audit.log`) — Linux Audit
- `journald` (via `journalctl -o json`)
- `fail2ban` (`/var/log/fail2ban.log`)

**Módulos**:
- `audit.rs` — parser de linhas audit, agrupa records por audit_id, suporta
  double/single-quoted nested fields + extração de `{ action }` dos AVC
- `journal.rs` — JSON-lines do journalctl, mapeia `PRIORITY` syslog (0-7)
- `fail2ban.rs` — parser de `YYYY-MM-DD HH:MM:SS,mmm logger [pid]: LEVEL [jail] Action IP`
- `event.rs` — enum `Event { Audit, Journal, Fail2ban }` + `Severity` shared
- `narrator.rs` — dispatch pt-BR para cada tipo (15+ tipos audit cobertos)
- `correlator.rs` — 4 patterns:
  - `fail2ban_burst`: N×Found mesmo IP → Ban em 2min (N≥2)
  - `oom_kill`: journal CRIT OOM, opcionalmente confirmado por audit ANOM_ABEND
  - `selinux_burst`: 3+ AVC denials mesmo comm em sliding window 60s
  - `suspicious_ssh_login`: Accepted publickey + Found anterior em fail2ban (10min)
- `live.rs` — `LiveSources` com `refresh()` para tail mode (polling 2s default)
- `tui.rs` — Ratatui App: lista navegável, filtros (`f`/`s`/`/`), live indicator
- `main.rs` — clap CLI com `--sources`, `--output`, `--limit`, `--min-severity`, `--follow`

**Output modes**: `tui` (default), `text`, `json`, `json-bundle` (com source
discriminator — usado pela GUI), `correlations`.

**Tests**: 28 unit tests passando.

**Distribuição preparada**: RPM spec em `packaging/vigia-activity-log.spec`
pronto para COPR. Tag `v0.7.0` criada no GitHub.

---

### 5.3 Vigia Activity Log — GUI (`tools/activity-log-gui/`, v0.1.0)

**Função**: Frontend GTK4 do core Rust. Roda `vigia-log --output json-bundle`
em background, parseia e renderiza visualmente.

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Tabs**: Linha do tempo (lista filtravel) + Correlations (cards) + Sobre.

**Padrão**: lança `vigia-log` async via `threading.Thread`, lê stdout JSON,
faz `GLib.idle_add` para atualizar UI. Sem reimplementação do parser em
Python.

**Wrapper de**: `vigia-log` (binário Rust próprio — único caso em que
"wrapped package" é ferramenta do próprio VigiaOS).

---

### 5.4 Vigia Privacy Controls (`tools/privacy-controls/`, v0.3.1)

**Função**: 13 toggles de privacidade em uma única janela.

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Toggles por categoria**:

| Categoria | Toggles |
|---|---|
| Localização | Serviços de localização (user-scope, dconf) |
| Telemetria | Bloquear relatórios técnicos |
| Histórico | Arquivos recentes, Uso de apps, Identidade |
| Lock Screen | Auto-lock, Prévia notificações |
| Limpeza Automática | Lixeira, Temp files |
| Rede (system) | Firewall (firewalld), SSH |
| Dispositivos | Bluetooth |

**System-scope** usa `pkexec systemctl enable/disable --now <unit>`.

**Wrapper de**: `dconf`, `systemd`, `bluez`.

---

### 5.5 Vigia SELinux Manager (`tools/selinux-gui/`, v0.2.0)

**Função**: GUI moderno para SELinux. 6 tabs + Sobre.

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Tabs**:
- Status — modo runtime + persistent (edita `/etc/selinux/config`)
- Booleans — lista pesquisável com descrições pt-BR (~60 booleans cobertos)
- Denials — `pkexec ausearch -m AVC` + botão "Gerar" audit2allow
- Files — `pkexec restorecon` com path input
- Network — `semanage port -l` (read-only)
- Processes — `ps -eZ -o label,pid,user,comm` (read-only)
- Sobre

**Performance**: lazy tabs + threaded init (Batch 1, P2). Tab não constrói
conteúdo até ser selecionada pela primeira vez.

**Wrapper de**: `policycoreutils`, `setools-console`, `audit`.

---

### 5.6 Vigia Firewall Manager (`tools/firewall-gui/`, v0.1.0)

**Função**: Gerenciar firewalld (zonas, services, portas).

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Tabs**: Status + Zones (CRUD services + portas) + Sobre.

**Padrão write**: sempre `--permanent` + `--reload` (persiste no boot E
aplica imediato).

**Defaults**: minimum surface area. Tool não habilita services sem
confirmação explícita.

**Wrapper de**: `firewalld`.

---

### 5.7 Vigia Network Monitor (`tools/netmon-gui/`, v0.1.1)

**Função**: Conexões TCP/UDP em tempo real.

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Tabs**: Conexões + Listening + Sobre.

**Modo admin opt-in**: Switch na UI que, quando ON, faz backend chamar
`pkexec ss -tunap` (revela nomes de processos do sistema). Auto-refresh
desabilitado nesse modo (smart: não spammar polkit).

**Performance (Batch 1, P3+P7)**: single fetch reaproveitado pelas 2 tabs +
auto-refresh smart (pausa quando modo admin ON).

**Wrapper de**: `iproute2` (binário `ss`).

---

### 5.8 Vigia Hardening Checks (`tools/hardening-checks/`, v0.1.4)

**Função**: Wrapper de Lynis. Roda `lynis audit system`, parseia
`/var/log/lynis-report.dat`, renderiza findings categorizados.

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Tabs**: Visão geral + Avisos + Sugestões + Sobre.

**Particularidades Silverblue**: banners contextuais explicando que
findings de `/usr` read-only não são acionáveis no Silverblue (vs Workstation
mutável). Reduz ruído cognitivo.

**Bugfixes históricos**:
- v0.1.1 (`3b9e0ab`): `lynis-report.dat` é `0600` por default (root only).
  Fix: `pkexec bash -c 'lynis audit system; chmod 644 /var/log/lynis-report.dat'`
  no mesmo dialog (1 só prompt polkit).
- v0.1.2 (`66345df`): `tests_executed` no relatório é pipe-separated list de
  IDs, não inteiro. Fix: `len([t for t in value.split('|') if t.strip()])`.

**Wrapper de**: `lynis`.

---

### 5.9 Vigia Reports (`tools/reports/`, v0.1.1)

**Função**: Gera PDF/HTML com narrativa LGPD-friendly a partir do JSON do
Activity Log.

**Stack**: Python + GTK4 + Jinja2 + WeasyPrint.

**Tabs**: Gerar + Histórico + Sobre.

**Templates** (Jinja2):
- "Atividade dos últimos 7 dias"
- "Eventos suspeitos"
- "Acessos administrativos"

**Modo admin** (`v0.1.1`, `736b525`): 1 dialog polkit que ganha acesso a
audit log + escreve PDF. Sem múltiplos prompts.

**LGPD permissions**: PDFs gerados em `~/.local/share/vigia-reports/`
com `chmod 0600`.

**Wrapper de**: `vigia-log` (core Rust) + Jinja2/WeasyPrint (libs Python).

---

### 5.10 Vigia File Integrity (`tools/file-integrity/`, v0.2.1)

**Função**: Wrapper de AIDE (Advanced Intrusion Detection Environment) para
integridade de sistema, **+ hashing ad-hoc** (SHA-256/512/1, MD5) e
baseline-diff de diretórios em escopo de usuário — fusão do antigo Hash Tools
(merge na v0.2.0, task #68).

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Tabs** (6): Status (AIDE) + Mudanças (AIDE) + Hash + Verificar + Baseline +
Sobre. As 3 últimas (Hash/Verificar/Baseline) vieram do merge com Hash Tools —
escopo de usuário, sem root, complementam o AIDE de sistema.

**Perfil Silverblue customizado** (`3bc9057`): AIDE padrão do Fedora vasculha
`/usr` que é read-only no Silverblue (ruído inútil). Perfil custom foca em:
- `/etc` (configs mutáveis)
- `/root` (home do admin)
- `/var/spool/cron`, `/etc/crontab`, `/etc/cron.d`

**Exclude path** (polish v0.2, `e5011e4`): `/etc/systemd/system.control/` —
arquivos gerados pelo systemd ao aplicar `CPUWeight`/`MemoryLow` em slices,
voláteis por design, geram 10+ "modified" por check.

**Bugfixes históricos**:
- v0.1.1 (`5efe8b1`): AIDE ≥0.16 só aceita prefix `file:` em
  `database_in=`/`database_out=`, não em `database=`.
- v0.1.2 (`340cabc`): `/var/lib/aide/` é `0700` por default — `Path.is_file()`
  da UI (user) não conseguia stat. Fix: `chmod 755 /var/lib/aide/` no mesmo
  pkexec do init/update.

**LGPD permissions**: report files `chmod 0600`.

**Wrapper de**: `aide` (AIDE, sistema) + `hashlib` stdlib (hashing/baseline
ad-hoc do usuário, sem subprocess).

---

### 5.11 Vigia Tool Installer (`tools/tool-installer/`, v0.2.0)

**Função**: Catálogo curado de ferramentas de segurança instaláveis via
`rpm-ostree install` ou `flatpak install`. **v0.2** adicionou a aba
**Extensões de Navegador** (recomendações FOSS: uBlock Origin, Privacy Badger,
ClearURLs, LibRedirect) que abrem direto na AMO/Chrome Web Store.

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Categorias** (13 pacotes em `catalog.py`, 5 categorias):
- Auditoria e hardening — lynis, aide, chkrootkit, rkhunter
- Rede — mtr, nethogs
- Monitoramento e diagnóstico — lsof, strace, fail2ban
- Privacidade e criptografia — NetworkManager-openvpn-gnome, dnscrypt-proxy
- Forense e análise — clamav, hashdeep

Recon ativo e RE (`nmap`, `tcpdump`, `binwalk`) ficam **fora de
propósito** — são perfil ofensivo, reservados pro futuro **VigiaRed**
(§10.5). O foco do catálogo aqui é defesa/auditoria/privacidade.

**Padrão**: chama `pkexec rpm-ostree install <pkg>` async + status visual.
Reboot recomendado após install.

**Lazy refresh** (Batch 1, P1): catálogo carrega em thread, UI mostra
skeleton até concluir.

**Posicionamento no Hub**: NÃO aparece na sidebar de tools — fica como
ícone fixo na nav lateral fina (visual de "settings"), não compete com
ferramentas de uso diário.

**Wrapper de**: `rpm-ostree`, `flatpak`.

---

### 5.12 Vigia DNS Manager (`tools/dns-manager/`, v0.4.1)

**Função**: DNS focado em privacidade — wrappa o `dnscrypt-proxy` (DoH/DNSCrypt
com DNSSEC + no-logs). A v0.3 removeu o "modo simples" (systemd-resolved);
desde então é **dnscrypt-proxy only**.

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Tabs** (3): Status + Provedores + Sobre. (v0.4.0 removeu Blocklists e Stats —
bloqueio de ads/trackers é trabalho de extensão de navegador, não de DNS.)

**Catálogo (11 servers curados)** em `dnscrypt_catalog.py`: Cloudflare
(Standard/Security/Family), Quad9 (Standard/unfiltered), AdGuard (DNS/Family),
Mullvad (Standard/AdBlock), Quad9 DNSCrypt e Anonymized Relay. Filtros +
1-click apply.

**Migração 1-click** (`migration.py`): "Ativar dnscrypt-proxy" faz backup do
`systemd-resolved`, aponta `/etc/resolv.conf` → 127.0.0.1 e sobe o serviço;
"Restaurar systemd-resolved padrão" reverte. Tudo via `pkexec`.

**LGPD/privacidade**: query log off por default (minimum-surface); quando
ligado fica local; backups de config `chmod 0600`; recomenda servers no-logs
(Quad9, Mullvad, Anonymized Relay).

**Pré-requisito**: `dnscrypt-proxy` instalado (via Tool Installer ou
`rpm-ostree install dnscrypt-proxy`).

**Wrapper de**: `dnscrypt-proxy` (config TOML) + `systemd-resolved` (restore).

---
### 5.13 Vigia Capabilities Inspector (`tools/capabilities-inspector/`, v0.1.0)

**Função**: Audit de Linux capabilities. Lista binários com capabilities
setadas via `getcap -r /`, mostra detalhes pt-BR de cada capability.

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Tabs**: Visão Geral + Binários (com filtros) + Capabilities (catálogo) +
Sobre.

**Catálogo de 41 capabilities** com classificação de risco pt-BR:
- **11 ALTO** (CAP_SYS_ADMIN, CAP_NET_ADMIN, CAP_SYS_PTRACE, etc.)
- **17 MÉDIO** (CAP_NET_RAW, CAP_DAC_OVERRIDE, etc.)
- **13 BAIXO** (CAP_AUDIT_READ, CAP_CHOWN, etc.)

**Modo v0.1**: read-only audit. Modificação de capabilities (`setcap`)
fica para v0.2 — usuário precisa entender o que está mudando antes de ter
power tools pra isso.

**SVG**: lupa (magnifier) com check + X internos.

**Wrapper de**: `libcap` (binário `getcap`).

---

### 5.14 Vigia Antivirus (`tools/antivirus/`, v0.1.1)

**Função**: Antivirus on-demand para Linux desktop, wrapper de ClamAV.

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Tabs**: Status (estado + scans recentes) + Scan (alvo + run + findings) +
Base de dados (info + freshclam update) + Sobre.

**Substituição do `clamtk`**: o clamtk tinha UI envelhecida e quebrava
com frequência em GTK4. Vigia Antivirus provê GUI nativa libadwaita.

**Streaming**: scan async via `subprocess.Popen` lendo stdout linha-a-linha
em thread + `GLib.idle_add` para atualizar UI. Findings aparecem em tempo
real conforme detectados.

**Update de base**: `pkexec freshclam` num só dialog. Aceita rc=0 (atualizado)
ou rc=1 (já atualizado) como sucesso.

**Histórico**: reports em `~/.local/share/vigia-antivirus/scan-<timestamp>.json`
com `chmod 0600` (LGPD).

**Atalhos de target**: Home, Downloads, Documents, /tmp para escolha rápida.

**SVG**: shield com vírus (círculo + spikes) no centro.

**Wrapper de**: `clamav` (binário `clamscan`) + `clamav-update` (binário
`freshclam`).

---

### 5.15 Vigia Dashboard (`tools/dashboard/`, v0.2.1)

**Função**: Dashboard de sistema em tempo real — CPU, memória, disco
I/O, rede e processos com gráficos visuais.

**Stack**: Python + PyGObject + GTK4 + libadwaita + **Cairo** (drawing
custom para gráficos).

**Tabs**: Visão Geral + Recursos + Processos + Sobre.

**Substituições**:
- `htop` / `btop` → Visão Geral + Recursos + Processos
- `glances` → Visão Geral (overview multi-recurso)
- `iotop` → Recursos (agregado por device; per-process I/O em v0.2)
- `iftop` → Recursos (agregado por interface; per-process em v0.2)
- `sensors` → Recursos (CPU temp se `lm_sensors` instalado)

**Fonte de dados** (`backend.py`, 100% `/proc` + `/sys`):
- `/proc/stat` → CPU times por core → delta vs prev = %
- `/proc/meminfo` → RAM, swap, cache, buffers
- `/proc/loadavg` → load 1/5/15min
- `/proc/diskstats` → sectors_read/written por device → MB/s
- `/proc/net/dev` → RX/TX bytes por interface → MB/s
- `/proc/<pid>/stat,status,statm,cmdline` → processos
- `/sys/class/thermal/thermal_zone*/temp` → CPU temp
- `/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq` → frequência
- Sem subprocess (exceto fallback de `kill` via `pkexec` para PIDs alheios)

**Gráficos** (`graphs.py`, 3 widgets Cairo):

| Widget | Uso | Tamanho típico |
|---|---|---|
| `Sparkline` | Mini gráfico de linha para Visão Geral | 200×42 |
| `LineChart` | Multi-série com grid + labels Y + legenda | 400×160 |
| `StackedBar` | Barra horizontal segmentada (RAM used/cache/free) | full × 24 |

Cada widget tem:
- `set_draw_func()` ligado em `_on_draw()` (Cairo context)
- `deque(maxlen=60)` para histórico de 60s
- Push de valor → `queue_draw()` no widget

**Cores semânticas** (paleta Vigia, em `__init__.py`):
- CPU = emerald `#34d399`
- RAM = amber `#fbbf24`
- Disco = cyan `#22d3ee`
- Rede = violet `#a78bfa`

**Refresh**:
- Visão Geral, Recursos: 1Hz (`GLib.timeout_add(1000, callback)`)
- Processos: 0.5Hz (2s — listar 200+ procs é mais pesado)
- Ao destruir widget: `GLib.source_remove()` para parar timeout

**Processos — recursos especiais**:
- `_PROC_CPU_PREV` global: cache de `(total_ticks, snap_time)` por PID
  para calcular `%CPU` vs leitura anterior
- `_USER_CACHE` global: cache de `uid → username` (evita lookup repetido)
- `_CLOCK_TICKS` constante: `sysconf(SC_CLK_TCK)` — base do delta de CPU
- Limpeza automática de PIDs mortos do cache a cada refresh

**Kill com fallback admin**:
```python
try:
    os.kill(pid, signal.SIGTERM)
    return True, ""
except PermissionError:
    # Fallback: pkexec kill -TERM <pid>
    subprocess.run(["pkexec", "kill", "-TERM", str(pid)], ...)
```

**Filtros (Processos)**:
- Search: substring em `comm` ou `cmdline`
- Sort: `cpu`, `mem`, `pid`, `name`
- "Apenas meus processos": filtra `p.user == my_user`
- Limit fixo: top 30 (após filtro)

**SVG**: 4 mini-painéis em 2×2 (line chart emerald, bar chart amber,
arc cyan, area chart violet) — preview do que a tool faz.

**Sem persistência**: ao fechar a tool, histórico some. Diferente de
Activity Log / Reports / File Integrity que persistem. Por design —
dashboard é "agora", não "histórico".

**Wrapper de**: `procfs` (kernel interface, sem pacote externo).
Opcional: `lm_sensors` para sensores extras.

---

### 5.16 Vigia Rootkit Scanner (`tools/rootkit-scanner/`, v0.2.0)

**Função**: Wrapper unificado de **chkrootkit** + **Rootkit Hunter (rkhunter)**.
v0.2.0 reescrito do zero com o mesmo pattern PreferencesGroup do Antivirus.

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Tabs** (4): chkrootkit (scan rápido ~30s) + Rootkit Hunter (scan completo
2-5min) + Histórico + Sobre.

**Streaming**: scan async via `subprocess.Popen` lendo stdout linha-a-linha em
thread + `GLib.idle_add` (igual Antivirus). Saída estilo terminal.

**Histórico/LGPD**: reports JSON em `~/.local/share/vigia-rootkit/scans/` com
`chmod 0600`.

**Pré-requisitos**: `chkrootkit` + `rkhunter` (instaláveis via Tool Installer).

**Wrapper de**: `chkrootkit`, `rkhunter`.

---

### 5.17 Vigia Deployments Manager (`tools/deployments-manager/`, v0.1.1)

**Função**: GUI para os **deployments do `rpm-ostree`** — os snapshots
imutáveis que aparecem no GRUB. Lista (atual/rollback/staged/pinados),
rollback, pin/unpin, cleanup e alerta de `/boot` cheio.

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Tabs**: Deployments (lista + ações) + Limpeza (cleanup + alerta `/boot`) +
Sobre.

**Operações** (elevadas via `pkexec`): `rpm-ostree rollback`,
`rpm-ostree cleanup -p -r -m`, pin/unpin. Alerta de `/boot`: banner amarelo
>70%, vermelho >85%.

**Labels + notas LGPD**: rpm-ostree não suporta nome custom nativo; o Vigia
guarda labels/notas por checksum em `~/.config/vigia-deployments/state.json`
(`chmod 0600`) — display-only, como evidência de processo de mudanças.

**Histórico nativo**: checksums + timestamps do próprio rpm-ostree.

**Wrapper de**: `rpm-ostree`.

---

## 6. Padrões e convenções comuns

### 6.1 Stack consistente

- **GUIs**: Python 3.11+, PyGObject, GTK 4, libadwaita.
- **CLIs perfance-críticas**: Rust 2021 + Ratatui + Crossterm.
- **Sem deps externas pip** se possível (PyGObject vem do RPM
  `python3-gobject`). Exceção: `reports/` usa Jinja2 + WeasyPrint.

### 6.2 Estrutura de cada ferramenta Python

```
tools/<nome>/
├── pyproject.toml             # entry_point: vigia-<nome>
├── README.md                  # setup + features + roadmap
├── .gitignore
├── data/
│   ├── br.com.vigia.<Name>.desktop
│   └── br.com.vigia.<Name>.svg  (256x256, paleta VigiaOS)
└── src/vigia_<nome>/
    ├── __init__.py            # __version__, __app_id__, WRAPPED_PACKAGES
    ├── __main__.py            # entrypoint standalone
    ├── app.py                 # Adw.Application
    ├── window.py              # janela principal standalone
    ├── embed.py               # exporta build_content() -> Gtk.Widget
    ├── backend.py             # subprocess wrappers
    └── tabs/                  # se a janela tem múltiplas tabs
        ├── __init__.py
        ├── _helpers.py        # show_error, make_clamp, md_to_pango (duplicado — refator pendente)
        ├── about.py           # aba Sobre (padrão em toda tool)
        └── <tab>.py
```

### 6.3 `__init__.py` padrão

```python
"""Vigia <Nome> — descrição curta."""

__version__ = "0.1.0"
__app_id__ = "br.com.vigia.<Name>"

WRAPPED_PACKAGES = ["pacote-upstream", "outro-binario"]
```

`WRAPPED_PACKAGES` é lido pelo Hub para renderizar a sub-bar do header.

### 6.4 Ícones SVG

Formato: 256x256 viewBox.

Estrutura padrão:
- Fundo: rounded square (rx=48), gradient zinc-900 → zinc-950
- Glow radial sutil emerald (opacidade 0.18-0.20)
- Motivo central da ferramenta (eye, padlock, shield, brick wall, tunnel,
  globe, magnifier, etc.)
- Wordmark inferior: "VIGIA·<TOOL>" em JetBrains Mono, com `·` em emerald

Paleta:
- `#09090b` — zinc-950 (bg principal)
- `#18181b` — zinc-900 (bg cards)
- `#fafafa` — zinc-50 (texto principal)
- `#34d399` — emerald-400 (accent)
- `#fbbf24` — amber-400 (warning)
- `#f87171` — red-400 (error)

### 6.5 Privilege escalation via pkexec — NUNCA sudo

**Regra fixa (feedback-pkexec-not-sudo)**: privilege escalation sempre via
in-app polkit dialog (pkexec). NUNCA sudo direto.

Padrão para operações que precisam root:

```python
def set_something(value):
    if shutil.which("pkexec") is None:
        raise RuntimeError("pkexec nao encontrado. Instale 'polkit'.")
    result = subprocess.run(
        ["pkexec", "comando", "args"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout).strip()
        if "Request dismissed" in stderr or result.returncode == 126:
            raise RuntimeError("Autenticacao cancelada pelo usuario.")
        raise RuntimeError(f"... falhou: {stderr}")
```

**Combinar ops num só pkexec**: para evitar múltiplos prompts, agrupar
em `pkexec bash -c '...; ...; ...'`. Padrão usado em Hardening Checks
(roda lynis + chmod do report) e File Integrity (init + chmod do `/var/lib/aide`).

### 6.6 Async subprocess pattern (Batch 1)

Para evitar UI freeze:

```python
def _on_button_clicked(self, _btn):
    self._set_running(True, "Carregando...")
    threading.Thread(target=self._worker, daemon=True).start()

def _worker(self):
    try:
        result = backend.do_blocking()
        err = None
    except Exception as e:
        result, err = None, str(e)
    GLib.idle_add(self._on_done, result, err)

def _on_done(self, result, err):
    self._set_running(False)
    if err:
        show_error(self, "Falhou", err)
    else:
        self._render(result)
    return False  # GLib idle: one-shot
```

### 6.7 Adw.Clamp para limitar largura

Tabs custom (`Gtk.Box`) precisam Clamp manual. Tabs `Adw.PreferencesPage`
já clampam por padrão. Padrão em `_helpers.py`:

```python
def make_clamp(child, maximum_size=720):
    clamp = Adw.Clamp(maximum_size=maximum_size)
    clamp.set_child(child)
    return clamp
```

### 6.8 Markdown leve → Pango (feedback-ui-text)

Descrições longas usam markdown leve para legibilidade:

```python
description = (
    "Frontend **GTK4** do `vigia-log`. Consolida `audit.log`, "
    "`systemd journal` e `fail2ban.log` numa *unica linha do tempo*."
)
# Renderizar: md_to_pango(description) → <b>GTK4</b> do <tt>vigia-log</tt>...
```

Sintaxes: `**bold**`, `*italic*`, `` `code` ``. Sem full Markdown.

### 6.9 LGPD: report files são `0600`

Qualquer arquivo gerado pelas tools contendo dados sensíveis (logs, PDFs,
findings) → `chmod 0600` (owner read-only).

Aplicado em: Reports (PDFs em `~/.local/share/vigia-reports/`),
File Integrity (history em `~/.local/share/vigia-integrity/`).

### 6.10 Defaults restritivos (feedback-minimum-surface)

Contexto LGPD/advocacia: clientes confiam dados sensíveis. Defaults
restritivos, abrir só o necessário.

- Firewall: zona default `block`, não `public`
- DNS: sem upstream automático (usuário escolhe provider)
- VPN: sem auto-connect
- Services system-scope: opt-in via Privacy Controls

### 6.11 Instalação .desktop + icon

```bash
mkdir -p ~/.local/share/applications ~/.local/share/icons/hicolor/scalable/apps
cp data/<app-id>.desktop ~/.local/share/applications/
cp data/<app-id>.svg ~/.local/share/icons/hicolor/scalable/apps/
gtk-update-icon-cache ~/.local/share/icons/hicolor 2>/dev/null || true
update-desktop-database ~/.local/share/applications 2>/dev/null || true
```

### 6.12 Sudo + pip --user (armadilha conhecida)

Problema: `pip install --user` instala em `~/.local/bin/`, sudo não vê.
Solução: symlink em `/usr/local/bin/` (mutável no Silverblue):
```bash
for tool in vigia-hub vigia-dashboard vigia-privacy vigia-selinux vigia-firewall \
            vigia-netmon vigia-hardening vigia-reports vigia-integrity vigia-installer \
            vigia-dns vigia-caps vigia-log-gui vigia-antivirus vigia-rootkit \
            vigia-deployments; do
  sudo ln -sf "$HOME/.local/bin/$tool" /usr/local/bin/$tool
done
```

---

## 7. Como adicionar uma ferramenta nova

1. **Cria o diretório** `tools/<nome>/`
2. **Copia estrutura** de uma ferramenta existente (e.g., `dns-manager` se
   for tool simples, ou `selinux-gui` se vai ter muitas tabs)
3. **Adapta** `pyproject.toml` (nome, version, entry_point),
   `__init__.py` (`__app_id__`, `WRAPPED_PACKAGES`)
4. **Implementa** `backend.py` + `window.py` + `tabs/` + `embed.py`
5. **Desenha ícone** SVG 256x256 (rounded square zinc + emerald + motivo + wordmark)
6. **Cria** `data/<app-id>.desktop`
7. **Adiciona ao registry do Hub** em `tools/vigia-hub/src/vigia_hub/registry.py`:
   ```python
   ToolEntry(
       id="meu-tool",
       name="Meu Tool",
       description="...",
       long_description="...",  # Markdown leve
       features=[...],
       icon_path=_TOOLS_DIR / "meu-tool" / "data" / "br.com.vigia.MeuTool.svg",
       exec_cmd=["vigia-meu-tool"],
       embedded_module="vigia_meu_tool.embed",
       category="defesa",  # ou "monitoramento", "privacidade", "relatorios"
       wrapped_packages=["pacote-upstream"],
       available_fn=lambda: shutil.which("vigia-meu-tool") is not None,
   ),
   ```
8. **Atualiza** `README.md` do root
9. **Adiciona seção** neste `DEVELOPMENT.md` (subseção 5.X)
10. **Commit** com mensagem padrão: `Add Vigia <Name> v0.1 + register in Hub`

---

## 8. Setup numa máquina nova (Silverblue limpa)

### 8.1 Layer dependencies via rpm-ostree

```bash
sudo rpm-ostree install \
    git rust cargo \
    python3-gobject python3-pip \
    libadwaita gtk4 \
    aide lynis \
    dnscrypt-proxy \
    clamav clamav-update \
    chkrootkit rkhunter
systemctl reboot

# Nota: o hashing ad-hoc (aba Hash do File Integrity) usa hashlib do Python
# puro — nao precisa instalar nada. AIDE cuida do baseline de integridade.
```

(`reports/` requer adicional `python3-jinja2 python3-weasyprint` — instalar
se for usar essa tool.)

### 8.2 Clone + instalar todas as ferramentas

```bash
mkdir -p ~/dev && cd ~/dev
git clone https://github.com/andre28abr/VigiaOS.git
cd VigiaOS

# Activity Log core (Rust)
cd tools/activity-log
cargo build --release
sudo install -m 0755 target/release/vigia-log /usr/local/bin/vigia-log

# Tools Python — editable install user-scope
for d in vigia-hub privacy-controls selinux-gui firewall-gui netmon-gui \
         hardening-checks reports file-integrity tool-installer \
         dns-manager capabilities-inspector activity-log-gui \
         antivirus dashboard rootkit-scanner deployments-manager; do
  (cd ../$d && pip install --user -e .)
done

# Symlink em /usr/local/bin para acesso via sudo
for tool in vigia-hub vigia-privacy vigia-selinux vigia-firewall vigia-netmon \
            vigia-hardening vigia-reports vigia-integrity vigia-installer \
            vigia-dns vigia-caps vigia-log-gui \
            vigia-antivirus vigia-dashboard vigia-rootkit \
            vigia-deployments; do
  sudo ln -sf "$HOME/.local/bin/$tool" /usr/local/bin/$tool
done

# Entry no menu GNOME (só o Hub recomendado — ele lança as outras)
mkdir -p ~/.local/share/applications ~/.local/share/icons/hicolor/scalable/apps
cp tools/vigia-hub/data/br.com.vigia.Hub.desktop ~/.local/share/applications/
cp tools/vigia-hub/data/br.com.vigia.Hub.svg ~/.local/share/icons/hicolor/scalable/apps/
gtk-update-icon-cache ~/.local/share/icons/hicolor 2>/dev/null || true
update-desktop-database ~/.local/share/applications 2>/dev/null || true
```

### 8.3 install/bootstrap.sh (one-shot, auto-detecta a plataforma)

```bash
curl -fsSL https://raw.githubusercontent.com/andre28abr/VigiaOS/main/install/bootstrap.sh | bash
# Em sistema atômico: systemctl reboot ao final
```

Detecta atomic (`/run/ostree-booted`) vs Workstation e usa `rpm-ostree`
ou `dnf`. Instala deps + backends (lynis/clamav/…) + clona o repo + pip
installs as 16 tools + registra `.desktop`/ícones no GNOME + Flatpaks de
privacidade. **Não liga serviços** (tor/fail2ban/dnscrypt off — opt-in
nas tools). Guias por plataforma em `install/silverblue/` e
`install/workstation/`.

---

## 9. Log de implementação

> Ordem cronológica. Cada entrada cobre uma "release" ou iteração significativa.

### 2026-05-22 — Pivot v1 → v2 (distro → toolkit)
- Branch `legacy/v1-distro` preserva v1 (BlueBuild image)
- `main` resetado para layout toolkit
- `bootstrap.sh` substituiu `install.sh`
- Activity Log começou como primeira ferramenta

### 2026-05-22 — Activity Log v0.1 a v0.7
- v0.1: parser audit.log + narrator + TUI Ratatui básico
- v0.2: filtros (type cycle `f`, search `/`)
- v0.3: journald source + Event abstraction
- v0.4: fail2ban source
- v0.5: correlator (4 patterns)
- v0.6: severity classifier per-evento + `--min-severity`
- v0.7: live tail mode (-f)
- v0.7.1: 10+ narrators audit + Nerd Fonts column width
- packaging: RPM spec + Makefile + LICENSE + Tag `v0.7.0`

### 2026-05-22 — Privacy Controls v0.1 a v0.3
- v0.1: 3 toggles (Location, Telemetry, Bluetooth)
- v0.2: 7 toggles novos (Histórico, Lock Screen, Limpeza)
- v0.3: 3 toggles system-scope via pkexec (Firewall, SSH, Tor)

### 2026-05-22 — Vigia Hub v0.1 a v0.3.1
- v0.1: launcher básico em lista
- v0.2: grid de cards
- v0.3: master-detail (sidebar + content) + long_description
- v0.3.1: markdown leve nas descrições

### 2026-05-22 — SELinux Manager v0.1 a v0.2
- v0.1: 2 tabs (Status, Booleans)
- v0.2: 6 tabs (+ Denials/audit2allow, Files/restorecon, Network, Processes)
  + descrições pt-BR + persistent mode + Adw.Clamp

### 2026-05-22 — Firewall Manager v0.1
- Status + Zones CRUD via `pkexec firewall-cmd --permanent --reload`

### 2026-05-22 — Network Monitor v0.1 a v0.1.1
- v0.1: parser `ss -tunap` + 2 tabs (Conexões, Listening) + auto-refresh
- v0.1.1: Modo admin opt-in via pkexec

### 2026-05-23 — Hardening Checks v0.1
- Lynis wrapper inicial
- v0.1.1: fix crítico `chmod 644 lynis-report.dat` no mesmo pkexec
- v0.1.2: fix parser `tests_executed` pipe-separated

### 2026-05-23 — Reports v0.1
- Jinja2 + WeasyPrint + 3 templates LGPD
- v0.1.1: 1 dialog polkit no Modo admin + fix parser

### 2026-05-23 — File Integrity v0.1
- AIDE wrapper inicial
- v0.1.1: fix sintaxe `database_in=file:` (AIDE ≥0.16)
- v0.1.2: chmod 755 em `/var/lib/aide/` após init/update
- v0.1.3 (polish v0.2): exclude `/etc/systemd/system.control/`

### 2026-05-23 — Tool Installer v0.1
- Catálogo curado ~30 ferramentas via `rpm-ostree install`

### 2026-05-23 — Activity Log Python frontend v0.1
- `tools/activity-log-gui/` consome `vigia-log --output json-bundle`
- Core Rust mantido intacto, GUI virou wrapper visual

### 2026-05-23 — Hub v0.4.0: embedded mode
- `build_content() -> Gtk.Widget` por tool
- `importlib.import_module()` + cache no Hub
- Fallback subprocess se tool não disponível ou não embeddable

### 2026-05-23 — Batch 1 performance (commit `67b7e16`)
- Async subprocess em 5 tools (P1+P2+P3+P4+P5+P7)
- Tool Installer lazy refresh
- NetMon single fetch + auto-refresh smart
- SELinux lazy tabs + threaded init
- Firewall + Privacy threaded init
- SELinux/Firewall pkexec async

### 2026-05-23 — Batch 2 robustez (commit `4a850e2`)
- 9 fixes em bugs latentes (race conditions, exceptions silenciosas,
  timeouts curtos, detecção polkit cancel, etc.)

### 2026-05-23 — Silverblue tweaks (commit `3bc9057`)
- Perfil AIDE customizado (foco em `/etc`, `/root`, cron — pula `/usr`)
- Hardening Checks banners de contexto Silverblue vs Workstation

### 2026-05-23 — Hub v0.5.0: layout redesign (commit `3116410`)
- 3 painéis: nav lateral fina + sidebar média categorizada + content
- Categorias: Monitoramento, Privacidade, Defesa, Relatórios
- Tool Installer reposicionado para ícone fixo na nav fina
- Aba "Sobre" em todas as tools (`c900cb8`)

### 2026-05-24 — WRAPPED_PACKAGES sub-bar (commit `c4871e4`)
- Originalmente em `header.pack_end()` → comprimia tabs ("St...", "Bo...")
- Movido para `toolbar.add_top_bar()` com label "Wrapper de:" + pills
- Aplicado em todas as 9 tools que tinham tabs

### 2026-05-24 — VPN Manager v0.1 (commit `c06cdfa`)
- WireGuard wrapper inicial
- 3 tabs + heredoc UUID-delimited para safe write
- v0.1.1 (polish v0.2): paste fallback no dialog de import

### 2026-05-24 — DNS Manager v0.1 (commit `d0b4c37`)
- systemd-resolved wrapper
- 9 providers DoT (Cloudflare, Quad9, AdGuard, Mullvad, Google + variantes)
- `.vigia-backup` automático antes de cada write

### 2026-05-24 — Capabilities Inspector v0.1 (commit `3421c07`)
- getcap audit read-only
- Catálogo 41 capabilities pt-BR (11 ALTO + 17 MÉDIO + 13 BAIXO)
- Modificação (`setcap`) fica para v0.2

### 2026-05-25 — Polish v0.2 (commit `e5011e4`)
- AIDE exclui `/etc/systemd/system.control/`
- VPN dialog paste fallback (botão + grab_focus inicial)
- Bumps: file-integrity 0.1.2→0.1.3, vpn-manager 0.1.0→0.1.1

### 2026-05-25 — Docs (commit `5eebc9a`)
- DEVELOPMENT.md reescrito cobrindo 13 tools, layout redesign, polish history,
  embedded mode, roadmap atualizado

### 2026-05-25 — Security toolkit (4 tools novas)
Cycle "Security toolkit" — adiciona 4 tools de análise prática:

- **Vigia Antivirus v0.1**: wrapper ClamAV com streaming de findings,
  update via freshclam, atalhos de target (Home/Downloads/Documents/tmp).
  Substitui o clamtk (UI quebrada em GTK4).
- **Vigia Network Scanner v0.1**: wrapper nmap com 6 perfis pré-definidos
  (Discovery/Quick/Standard/Stealth/Aggressive/Full). Parse XML do nmap →
  Host/Port dataclasses. Validação de target contra shell injection.
  Banner ético + seção dedicada na aba Sobre.
- **Vigia Firmware Analyzer v0.1**: wrapper binwalk com 3 modos —
  Analisar (signatures), Extrair (binwalk -e), Entropia (edges +
  classificação qualitativa). Casos de uso documentados pra audit
  de firmware em camera IP / roteador num escritório.
- **Vigia Hash Tools v0.1**: 4 algoritmos (SHA-256/512, SHA-1, MD5).
  3 modos — Hash (single file), Verificar (expected vs computed),
  Baseline (snapshot JSON + diff added/modified/removed). Complementar
  ao File Integrity (AIDE).

Todas as 4 tools seguem o padrão da v2: `build_content() -> Gtk.Widget`,
4 tabs com aba Sobre, sub-bar `WRAPPED_PACKAGES`, reports em
`~/.local/share/vigia-<name>/` com `chmod 0600` (LGPD).

Hub registry expande de 11 para 15 entries (Tool Installer continua
fora da lista — fica no ícone fixo da nav lateral fina).

### 2026-05-26 — UI consistency pass (commits `2cd8862`, `8198df1`, `e089e2f`, `0b72ba8`)

3 passes consecutivos baseados em feedback do usuário (apos testar a
suite na VM):

1. **Botões action retangulares** (`2cd8862`): remove `.pill` de 27
   botões `.suggested-action` e `.destructive-action`. Padroniza forma
   pelo "Gerar" do Reports (retângulo com cantos suaves). Mantém pill
   em 3 chips compactos `.flat` (Home/Downloads/atalhos).

2. **Antivirus v0.1.1 UX** (`0b72ba8`): tab Status removida (era
   redundante). Banner inteligente `Adw.Banner` no topo da tab Scan
   só aparece quando há ação requerida (ClamAV não instalado, base
   desatualizada). 4 tabs → 3 tabs. Histórico de scans movido para
   tab "Base de dados".

3. **Padronização de espaçamentos** (`8198df1`): 26 arquivos atualizados
   via scripts Python (`/tmp/standardize_spacing*.py`):
   - Margens externas: 20/20/20/20 → 24/32/28/28
   - `header_lbl.set_margin_bottom`: 4 → 8
   - `header_desc.set_margin_bottom`: 16 → 24
   - `Adw.PreferencesGroup` secundários: `set_margin_top(24)`

4. **Botões fora dos cards** (`e089e2f`): Hash Tools tinha botões
   "Comparar", "Criar baseline", "Recarregar", "Copiar" dentro de
   `Adw.ActionRow` no card do `PreferencesGroup` — ficavam apertados.
   Movidos para `Gtk.Box` própria após o card, com `margin_top(16)`
   e `halign=END`. Spinners passam para esquerda do botão.

### 2026-05-26 — Vigia Dashboard v0.1 (commit `0258a94`)

Nova categoria de tool: **monitoramento de sistema em tempo real**.
Substitui htop/btop/glances/iotop/iftop em UI nativa.

- **4 tabs**: Visão Geral, Recursos, Processos, Sobre
- **Cairo charts**: Sparkline + LineChart + StackedBar (3 widgets
  custom em `graphs.py`, ~220 linhas)
- **Cores semânticas**: CPU emerald, RAM amber, Disco cyan, Rede violet
- **Refresh 1Hz** (Visão/Recursos) e 0.5Hz (Processos)
- **Backend 100% /proc + /sys** — sem subprocess, sem deps pip externas
- **Kill com pkexec fallback** para PIDs de outros users
- **Sem persistência** — histórico de 60s em deques circulares na memória

Hub registry: 15 → 16 entries. Dashboard é o **primeiro** da categoria
"monitoramento" (porta de entrada visual). Tool Installer ganha nota
em htop/iotop indicando que Dashboard cobre o mesmo escopo.

### 2026-05-26 — Dashboard v0.2 + vigia_common + COPR

3 grandes entregas numa sessão:

**1. Dashboard v0.2** (1 commit):
- `ProcessInfo` ganha: `read_mbs`, `write_mbs`, `n_tcp_established`,
  `n_tcp_listen`, `n_udp`
- Backend lê `/proc/<pid>/io` para per-process I/O com cache
  `_PROC_IO_PREV` (delta vs leitura anterior → MB/s)
- Backend mapeia socket inodes para PIDs via parse de
  `/proc/net/tcp{,6}/udp{,6}` + leitura de `/proc/<pid>/fd/*`
- Sort novo: "I/O (read+write)" e "Conexoes ativas"
- Nova tab "Alertas" com módulo `alerts.py`: `AlertRule`,
  `AlertManager`, persistência em `~/.config/vigia/dashboard-alerts.json`
  (mode 0600), notificação via `Gio.Notification`
- 4 regras default (todas opt-in): CPU>95%, RAM>90%,
  temp>85°C, disco/>95%
- Dashboard: 4 → 5 tabs

**2. vigia_common package** (1 commit):
- Nova lib interna em `tools/vigia-common/` (`pip install -e .`)
- Módulos: `helpers.py`, `markdown.py`, `badges.py`, constantes
  de layout em `__init__.py`
- 16 `_helpers.py` migrados: cada um vira arquivo fino que
  re-exporta de vigia_common + preserva constantes locais
  (CONTENT_MAX_WIDTH varia por tool: 720-1000)
- Funções específicas (severity_css, escape_markup, risk_css)
  ficam preservadas localmente
- `vigia_hub/markdown.py` esvaziado para re-export
- 18 `pyproject.toml` ganham `dependencies = ["vigia-common"]`
- Implementação via 2 scripts: `refactor_helpers.py` (regex +
  AST-light) + `add_dependency.py`
- **Retro-compatibilidade total**: código `from .._helpers import
  make_clamp` continua funcionando sem mudanças

**3. COPR packaging** (1 commit):
- 20 spec files RPM em `packaging/`:
  - `vigia-suite.spec` (metapackage — `Requires` os 19 pacotes)
  - `vigia-common.spec` (lib interna noarch)
  - `vigia-activity-log.spec` (Rust core, pre-existente)
  - 17 spec files para tools Python (gerados via script)
- `Makefile` com targets: srpm-all, rpm-all, copr-push, copr-setup
- `README.md` completo: setup COPR, build local, webhook SCM,
  bump de versão, detalhes técnicos
- **Status**: pronto para ativação, falta apenas criar conta COPR
  e configurar webhook (passos manuais documentados)

Total da sessão: 12 commits, ~3500 linhas adicionadas, 18 tools
afetadas por algum refator.

### 2026-05-27 — Enxuga & Polish (commits `5e34e9d`..`c835642`)

Limpeza de escopo (fase LGPD/escritório):

- **Removidas 3 tools**: Network Scanner, Firmware Analyzer, VPN Manager
- **Merge**: Hash Tools → File Integrity v0.2.0 (mesma categoria conceitual)
- **Privacy Controls v0.3.1**: fix alignment bug com `Adw.Bin` wrapper em `PreferencesPage`
- **Rootkit Scanner v0.2.0**: rewrite do zero seguindo pattern Antivirus (sem expansão de janela no Hub embedded)
- Suite passou de 20 → 16 → 17 tools (depois adicionou Rootkit + Deployments)

### 2026-05-28 — Deployments Manager v0.1 (commits `3a89deb`, `032d366`)

Nova tool de gerenciamento de deployments rpm-ostree (substitui o GRUB
de boot pra usuário não-técnico):

- **backend.py**: parser de `rpm-ostree status --json`, dataclass `Deployment`
- **state.py**: labels customizados + notas multilinha por checksum, em
  `~/.config/vigia-deployments/state.json` (chmod 0600)
- **3 tabs**: Deployments (rollback/pin/unpin), Cleanup (limpar pending/rollback/cached), Sobre
- Botões `Salvar` com `suggested-action` (azul) por feedback do user
- 37 testes (backend + state)

### 2026-05-28 — Hub v0.5.1→0.5.10 (Configurações completa)

Aba **Configurações** do Hub virou centro real de preferências em 3 fases:

**Fase 1a — Autostart XDG (v0.5.1):**
- Novo módulo `settings.py`: `Settings` dataclass + persistência em
  `~/.config/vigia-hub/settings.json` (chmod 0600, atomic write)
- Helpers `autostart_install/remove/sync/is_enabled` — gera/remove
  `~/.config/autostart/vigia-hub.desktop` (XDG padrão, com
  `X-GNOME-Autostart-Delay=10` pra dar tempo do DE carregar)
- **Sync com disco**: ao abrir aba, lê `.desktop` real e atualiza
  state.json caso user tenha editado manualmente
- 21 testes em `tests/hub/test_settings.py`

**Fase 1b — Tray icon + background mode + minimized (v0.5.3-0.5.4):**

Limitação técnica resolvida: GTK4 (Adw) e GTK3 (AppIndicator) **não
coexistem num mesmo processo PyGObject**. Solução: subprocess separado.

- Novo pacote `vigia_hub.tray/` com:
  - `checks.py` — detecta lib `libayatana-appindicator-gtk3` (via
    subprocess Python test) + extensão GNOME `appindicatorsupport@rgcjonas`
    (via `gnome-extensions list` / `list --enabled` — locale-agnostic)
  - `manager.py` — `TrayManager` que faz spawn/kill do subprocess via
    `subprocess.Popen` + `prctl(PR_SET_PDEATHSIG)` (Linux) pra child
    morrer se Hub crashar
  - `indicator.py` — script GTK3 standalone (entry point
    `vigia-hub-tray`) que cria `AyatanaAppIndicator3` com menu
    minimalista (Abrir Hub / Configurações / Sair)
- Comunicação tray ↔ Hub via D-Bus: Hub registra `Gio.SimpleAction`
  (show-window, show-settings, quit-hub) que o subprocess invoca via
  `org.gtk.Actions` interface
- **Background mode**: `app.hold()` quando tray ON; close-request da
  janela esconde em vez de matar processo
- **--minimized flag** em `__main__.py`: spawna tray, não apresenta
  janela na inicialização
- Auto-detect lib+ext faltando → dialog "Instalar agora" via
  `pkexec rpm-ostree install`
- 25 testes em `tests/hub/test_tray.py`

**Fase 2 — Bloqueio por senha Polkit (v0.5.5-0.5.10):**

5 iterações até chegar na implementação correta:

- v0.5.5: implementação síncrona usando `Polkit.Authority.check_authorization_sync` — **travou UI**
- v0.5.6: movi pra `threading.Thread` + `GLib.idle_add` — **ainda travou** (Polkit lib não é thread-safe)
- v0.5.7: tentei `wait_for_polkit_recognition` (race do polkitd inotify) — erro mudou pra "Action not registered"
- v0.5.8: removi progress dialog (modal sem botões capturava foco) — ainda travou (3 problemas combinados)
- **v0.5.9: REWRITE completo** — abandonei lib `PyGObject Polkit` e `.policy` custom:
  - Uso `pkexec /usr/bin/true` via `Gio.Subprocess.communicate_utf8_async`
  - Action default `org.freedesktop.policykit.exec` já existe em qualquer Polkit
  - Zero threads, zero deadlock D-Bus, zero `.policy` install
  - `handler_block_by_func` evita recursão do signal `notify::active`
- v0.5.10: **lazy auth** quando autostart+minimized — pop-up de senha não interrompe o login do GNOME, espera user clicar "Abrir Hub" no tray
- 24 testes em `tests/hub/test_auth.py`

**Lições aprendidas (consolidadas em §11):**
- PyGObject Polkit lib **não é thread-safe** — usar `Gio.Subprocess`
  com pkexec é mais robusto que API Polkit direta
- `gnome-extensions info` retorna stdout localizado (pt-BR/en) —
  usar `gnome-extensions list [--enabled]` que retorna só UUIDs
- Adw modal dialogs sem botões podem capturar foco indevidamente —
  preferir `set_sensitive(False)` + mudança de subtitle pra feedback
- GTK3 + GTK4 num mesmo processo Python = impossível (PyGObject só
  carrega uma versão) — split em subprocess + D-Bus

### Arquitetura do Hub embedded (atualizada v0.5.10)

```
┌────────────────────────────────────────────────────────────┐
│ vigia-hub (GTK4 + Adw)        application_id = br.com...   │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Adw.Application                                      │  │
│  │  ├─ Gio.SimpleAction: show-window/show-settings/quit │  │
│  │  ├─ TrayManager (spawn vigia-hub-tray)               │  │
│  │  ├─ do_activate:                                     │  │
│  │  │   ├─ if password_lock and NOT will_minimize:      │  │
│  │  │   │   check_auth() sync (antes da janela)         │  │
│  │  │   └─ if password_lock and will_minimize: lazy     │  │
│  │  └─ close-request: esconde se tray on                │  │
│  └──────────────────────────────────────────────────────┘  │
│         │  spawn (Popen)              ▲                    │
│         ▼                              │ D-Bus session bus │
└─────────┼─────────────────────────────┼────────────────────┘
          │                              │
          ▼                              │ org.gtk.Actions/Activate
┌─────────────────────────────────────┐ │
│ vigia-hub-tray (GTK3, subprocess)   │ │
│   AyatanaAppIndicator3              │ │
│   ├─ Abrir Hub      ──────────────────┘
│   ├─ Configurações  ─────────────────► show-settings
│   └─ Sair do Vigia  ─────────────────► quit-hub
└─────────────────────────────────────┘
```

### 2026-05-28 — Etapa E: Hardening das tools (robustez invisível)

Endurecimento defensivo de toda a suite, **sem mudança de UI** — o
objetivo é que entrada inesperada (arquivo de estado corrompido, JSON
válido mas com formato errado, saída de subprocess truncada) nunca
derrube uma tool.

**Auditoria de timeouts (resultado: 0 gaps):**
- Script AST custom varreu todas as chamadas `subprocess.run/
  check_output/check_call/call` procurando ausência de `timeout=`
- Confirmado **0 chamadas bloqueantes sem timeout** (já estava completo
  desde a Auditoria 3/4)
- `Popen` sinalizado e verificado caso a caso: `xdg-open` fire-and-forget
  (reports), clamscan/pkexec com `proc.wait(timeout=10)` (antivirus,
  rootkit), tray subprocess (intencionalmente long-lived), launch de
  tool (window.py) — todos corretos

**Gap real fechado — JSON válido com formato errado:**

Duas classes de falha de parsing: (1) JSON malformado → `JSONDecodeError`
(já tratado em todo lugar); (2) **JSON válido com shape errado** (lista/
string/int/null onde se espera dict, chaves faltando, tipos de campo
errados) → `AttributeError`/`TypeError`/`KeyError`, muitas vezes **fora**
do `except` existente. Essa segunda classe era o buraco.

Padrão aplicado em **12 funções de parsing** (9 tools + Hub):
- `if not isinstance(data, dict): return <default>` nos loaders
- `if not isinstance(d, dict): continue` por elemento de lista
- `try/except (ValueError, TypeError): continue` na coerção de campos
- `str(...)` em campos usados com `in`/regex
- helper `_safe_int(value, default=0)` (activity-log-gui)

Funções endurecidas: deployments `get_deployments`+`state._load`;
installer `rpm_ostree_status_raw`+`pending_changes`+`browser_extensions`;
file-integrity `load_state`+`compare_baseline_blocking`+`list_baselines`;
antivirus `list_recent_reports`; dashboard `load_rules`; activity-log-gui
`_parse_bundle`; rootkit `list_recent_reports`+`load_report`; reports
`_parse_json_lines`+4 journal parsers; Hub `load_settings`.

**Testes fuzz (rede de segurança, +30 testes):**
- 9 arquivos `tests/*/test_fuzz_*.py` jogam baterias de payloads
  malformados e de shape errado em cada parser
- Asseguram: nunca crasha + retorna o tipo de default seguro
- **Pegaram 1 bug real**: `[{"MESSAGE": 123}]` fazia `if "Accepted" in
  msg` levantar `TypeError` (int não é iterável) — fix: `str(...)` nos
  4 journal parsers do reports
- Suite total: **401 → 431 testes** (todos passando)

### 2026-05-28 — Etapa D (parte 1): Notificacoes desktop nativas

Primeira feature *visivel* da Etapa D. As tools agora avisam o usuario
via **notificacao nativa do GNOME Shell** (banner no topo + lista do
relogio), nao um popup proprio. Caso de uso central: rodar um scan
longo (rootkit 2-5min) e ir fazer outra coisa — quando termina, chega
o aviso mesmo com o Hub minimizado no tray.

**Helper compartilhado — `vigia_common/notifications.py`:**

Como as tools rodam *embedded* no Hub (mesmo processo), o helper pega a
`Adw.Application` em execucao via `Gio.Application.get_default()` e
dispara um `Gio.Notification` — protocolo padrao freedesktop, que no
GNOME e' o proprio Shell. Por isso aparece igual a qualquer app nativo.

- `notify(title, body, *, notif_id, priority, icon_name, default_action)`
  — primitiva. **No-op gracioso** (retorna False, nunca levanta) se nao
  ha app rodando (tool standalone, testes headless).
- `notify_if_unfocused(...)` — so notifica se **nenhuma janela do Vigia
  esta focada**. Se o user ainda olha a tool, o dialog in-app ja' avisa;
  o banner do sistema seria ruido. Usado pelos scanners.
- `notif_id` estavel por evento → reenviar **substitui** o banner
  anterior em vez de empilhar (anti-spam).
- `default_action='app.show-window'` (guardado por `lookup_action`):
  clicar a notif traz o Hub ao foco. Reusa a `Gio.SimpleAction` que o
  tray ja' registrava.

**Wiring (3 tools):**
- **Dashboard / Alertas**: refatorado pra usar o helper (antes tinha
  `Gio.Notification` inline + danca de `root.get_application()`).
  Mantem prioridade HIGH e `notif_id` por regra.
- **Rootkit Scanner**: chkrootkit + rkhunter notificam no fim do scan
  (infectado HIGH / warnings / limpo), via `notify_if_unfocused`.
- **Antivirus**: notifica no fim do scan (infectado HIGH / limpo).

**Por que GNOME-nativo importa:** persiste com a janela escondida
(modo tray/background, v0.5.3), respeita "Nao perturbe" e o toggle
por-app de Configuracoes → Notificacoes, e mostra o icone do Vigia
(vem do `.desktop` do Hub). Sem atrito de portal porque a suite e' RPM
(layered), nao Flatpak.

- 4 testes em `tests/common/test_notifications.py` (`@pytest.mark.gtk` —
  rodam na VM, skipados no dev sem GI). Suite: **431 → 435** (4 skip no Mac).

---

### 2026-05-28 — Antivirus: "Saida do scan" estilo terminal

Refinamento de UX no Antivirus pra alinhar com o Rootkit Scanner. Antes a
aba Scan tinha duas areas: uma lista *Findings* (cards) + um *Log do scan*
colapsado e sem cor. Agora e' um **unico terminal "Saida do scan"** que se
comporta igual ao chkrootkit/rkhunter:

- **Aberto por padrao** (`set_expanded(True)`), cursor invisivel, monospace.
- **Auto-scroll**: cada linha empurra a barra pro fim (`_scroll_to_end` via
  `create_mark`/`scroll_to_mark`/`delete_mark`), entao o usuario sempre ve
  o progresso do clamscan em tempo real.
- **Coloracao** (`insert_with_tags`): arquivo limpo `: OK` → **verde**
  (`#4ade80`, so o "OK"); linha `... FOUND` (ameaca) → **vermelha inteira**
  (`#f87171`); `SCAN SUMMARY` → **amber** (`#fbbf24`); `Infected files: N`
  do sumario → verde se `0`, vermelho se `>0`.
- **Linha-resumo garantida** no fim (`_append_summary_line`): `══ Nada
  suspeito ══` (verde), `══ N INFECTADO(S) ══` (vermelho) ou erro (vermelho)
  — sempre colorida, mesmo que o sumario do clamscan varie.

A lista *Findings* foi **removida**: o output completo do clamscan (linhas
`FOUND` + sumario) ja' aparece no terminal, e o `result.findings` continua
salvo no JSON do Historico independente da UI. Menos superficie, mesma info.

---

### 2026-05-28 — Padronizacao Antivirus ⇄ Rootkit Scanner

Alinhamento visual/funcional entre o **Antivirus (ClamAV)** e o **Rootkit
Scanner (chkrootkit + rkhunter)** pra os tres scanners se comportarem igual.

**Antivirus — aba Scan:**
- **Caixa de Estatisticas** (`Adw.PreferencesGroup` "Estatisticas"), mesmo
  pattern do Rootkit: *Arquivos escaneados*, *Infectados* (vermelho se >0),
  *Tempo decorrido*. Contadores ao vivo: `: OK` incrementa escaneados,
  ` FOUND` incrementa infectados — feedback durante scans longos. No fim, o
  summary do clamscan e' autoritativo (`scanned or live`, `max(result, live)`
  pra sobreviver a cancelamento no meio).
- **Seletor de alvo removido.** Em vez do `Gtk.Entry` + chips de preset, agora
  so ha' `[Iniciar scan] [Parar] [botao de pasta]`. Pasta vazia = **varredura
  do sistema todo** (`/`). O `_target_desc()` mostra o alvo no status label.
- **Header** renomeado de "Scan on-demand" → **"ClamAV"** com `HEADER_DESC`
  estilo Rootkit (markup explicando assinaturas + cores + full-scan default).
- Botao *Parar* fica sempre visivel mas desabilitado ate' o scan rodar
  (preserva o espaco), e o *Iniciar* desabilita enquanto roda.

**Backend (`scan_async`):**
- Varredura de `/` agora pula pseudo-filesystems via `--exclude-dir`
  (`^/proc ^/sys ^/dev ^/run`) — evita travar/poluir.
- `rc=2` so e' tratado como erro fatal se `scanned_files == 0`. Num scan de
  sistema inteiro como usuario comum, "Permission denied" em arquivos de
  outros donos gera `rc=2` mas nao e' fatal se o scan rodou de fato.
  *(Nota: full-scan roda como o usuario, sem pkexec — cobre tudo que e'
  world-readable; /root e afins ficam de fora. Root completo via pkexec
  fica como follow-up se necessario.)*

**Rootkit Scanner — chkrootkit + rkhunter:**
- Ganharam o `_tag_ok` (verde `#4ade80`) e coloracao de linhas "limpas":
  chkrootkit colore `not infected` / `nothing found`; rkhunter colore
  `[ OK ]` / `[ Not found ]` / `[ None found ]`.
- **Linha-resumo colorida** no fim do terminal (`_append_summary_line`),
  igual ao Antivirus: `══ Nada suspeito ══` (verde) / `══ N infectado(s) ══`
  (vermelho) / `══ N warning(s) ══` (amber) / cancelado / erro.

Resultado: os tres scanners tem header + estatisticas + terminal colorido +
linha-resumo no mesmo padrao. Suite segue **431 passed, 4 skipped**.

---

### 2026-05-28 — Etapa D (parte 2): tray quick actions + status + backup + CLI (Hub v0.7.0)

Fecha a Etapa D (parte 1 foi notificacoes desktop). Quatro entregas, todas
com backend **puro Python testavel** (sem GTK) reaproveitado entre GUI, tray
e terminal.

**1. CLI `vigia` (`cli.py`)** — novo entry point no `pyproject.toml`
(`vigia = vigia_hub.cli:main`). Subcomandos:
- `vigia status [--json]` — versao do Hub, flags de inicializacao
  (autostart/bandeja/bloqueio), quais dos 14 modulos estao instalados
  (`shutil.which`), binarios externos core (clamscan/freshclam/chkrootkit/
  rkhunter/aide/lynis), ultimo scan antivirus + rootkit, e backups.
- `vigia backup [ARQUIVO.zip]` / `vigia restore ARQUIVO.zip [--dry-run]`.
- `vigia version`. Sem subcomando → status resumido.

**2. `status.py` — fonte unica de verdade.** Puro Python, importavel tanto no
Hub GTK4 quanto no subprocess GTK3 do tray. `gather()` monta um `SuiteStatus`;
`format_text()` (terminal), `to_dict()` (JSON) e `tray_tooltip()` (linha curta)
renderizam. Le os relatorios de `~/.local/share/vigia-antivirus` e
`vigia-rootkit/scans` direto (sem cross-import de tools). `humanize_age()`
pt-BR ("ha 2 dias").

**3. `backup.py` — backup/restore `.zip` (0600, LGPD).** Empacota config
(`~/.config/vigia-hub|vigia|vigia-deployments|vigia-installer`) + dados
(`~/.local/share/vigia-antivirus|vigia-hash|vigia-reports|vigia-rootkit`) num
zip com `MANIFEST.json`. **Nao** inclui `data/vigia-hub` (cache de manuais +
a propria pasta de backups → evita backup recursivo). Zip criado 0600 via
tmp+replace; restauracao reaplica 0600 (arquivos) / 0700 (dirs). **Anti
Zip-Slip**: rejeita entradas com `..`, path absoluto, ou fora de
`config/vigia*` / `data/vigia*` — aborta sem extrair nada de zip suspeito.
Exposto na GUI em **Config. → Aplicacao → "Backup e restauracao"** (botoes
com `Gtk.FileDialog` + worker thread + `GLib.idle_add`).

**4. Tray — acoes rapidas + status vivo (`tray/indicator.py`).**
- Submenu **"Abrir modulo"** com atalhos diretos (Dashboard, Antivirus,
  Rootkit Scanner, File Integrity, Hardening) → nova action D-Bus
  `show-tool` (parametro string). `app.py` registra
  `Gio.SimpleAction.new("show-tool", GLib.VariantType.new("s"))`;
  `window.show_tool(tool_id)` troca pro modo tools + seleciona a row da
  sidebar.
- **Status no tooltip + item de info** do menu, atualizado a cada 120s via
  `GLib.timeout_add_seconds` chamando `status.tray_tooltip()`
  ("Vigia Hub 0.7.0 · 13/14 modulos · antivirus ha 2d (limpo)").

Testes novos: `tests/hub/test_backup.py` (24), `test_status.py` (24),
`test_cli.py` (8) — incluindo roundtrip, perms 0600 e os 5 cenarios de
Zip-Slip. Suite: **487 passed, 4 skipped**.

---

### 2026-05-28 — Etapa D (opcional): notificacoes AIDE + Lynis

Fecha a parte *opcional* da Etapa D. Na parte 1, so' 3 tools notificavam
(Dashboard, Antivirus, Rootkit). Agora os **scanners restantes** tambem
avisam pelo banner nativo do GNOME quando terminam com a janela fora de
foco (minimizado/tray ou em outro app) — experiencia consistente em
todos os modulos de varredura.

Mesmo padrao da parte 1 (`notify_if_unfocused` do `vigia_common`,
`notif_id` estavel por tool, HIGH quando ha achado / NORMAL quando
limpo). Wiring feito no **`window.py`** de cada tool (ponto onde o
relatorio ja' foi reparseado e distribuido pras abas), nao na aba:

- **File Integrity (AIDE)** — `v0.2.1`. `_IntegrityContent._on_check_done`
  chama `_notify_check(result)`: HIGH com `N mudanca(s)` (added · changed ·
  removed) se `summary.has_changes`, senao NORMAL "nenhuma mudanca"
  citando `total_entries`. `notif_id="vigia-integrity-check"`. Nao notifica
  em `not result.success` (erro ja' tratado in-app).
- **Hardening (Lynis)** — `v0.1.3`. `_HardeningContent._reload_and_refresh`
  chama `_notify_audit()`: HIGH com `N warning(s)` se houver, senao NORMAL,
  sempre citando o `hardening_index/100`. `notif_id="vigia-hardening-audit"`.
  No-op se `report.has_data()` for falso.

Bonus: alinhada a versao do File Integrity — `pyproject.toml` estava em
`0.1.3` mas `__init__.py` ja' declarava `0.2.0` (bump esquecido no merge do
Hash Tools, task #68); agora ambos em `0.2.1`.

Sem testes novos: a logica vive no `window.py` (acoplado a GTK, skipado no
dev sem GI) e `notify_if_unfocused` ja' e' no-op gracioso sem app. Suite
inalterada: **487 passed, 4 skipped**. So' `git pull` + reabrir o Hub na
VM (editable install — codigo reflete sem reinstalar; nao mudou entrypoint).

### 2026-05-29 — Auditoria de consistência + trim do catálogo

Pente-fino pós-enxugamento (drift acumulado das remoções de tools) +
decisão de escopo no Tool Installer. Commits `7a32a93`..`b38655b`.

- **Packaging & versões** (#81–#83, #86): removidos dirs/specs órfãos de
  tools já deletadas; specs Python normalizados (glob `dist-info`
  sistêmico); 5 versões `pyproject` ≠ `__init__` alinhadas; specs
  `caps`/suite corrigidos.
- **Robustez** (#79–#80): fix do argv do `pkexec` na notificação do
  Hardening; `status.py` do Hub blindado contra JSON malformado.
- **Testes** (#84): +68 casos de parser dedicados (Lynis/AIDE/ClamAV) —
  Hardening não tinha dir de teste. Fixture `no_default_app` consertada:
  `Gio.Application.set_default(None)` é rejeitado pelo binding GI
  (arg não-nulável), então monkeypatch de `get_default` no lugar. Suite:
  **564 passed, 4 skipped** no dev (mac); **568** na VM com GTK real.
- **Docs** (#85): DEVELOPMENT/README/tests sincronizados com as 16 tools
  reais (16 binários, `vigia-caps` não `vigia-capabilities`, etc.).
- **Trim do catálogo** (#87, `b38655b`): `nmap`, `tcpdump` e `binwalk`
  removidos de `catalog.py` (21→18 pacotes; rede 5→3, forense 3→2).
  Recon/sniffing/RE = perfil ofensivo → reservados pro **VigiaRed**
  (§10.5); `nmap`/`binwalk` eram os backends das GUIs Network Scanner e
  Firmware Analyzer já removidas. De quebra, descrições stale de
  `wireguard` (citava VPN Manager) e `dnscrypt-proxy` (citava "v0.2
  opt-in, sem UI") corrigidas, e o §5.11 (que descrevia um catálogo
  de ~30 ferramentas que não batia com o `catalog.py` real).

### 2026-05-30 — B5 + B1 + B4 + B3 + B2/B6 (sistema de instalação)

Início da execução do backlog §10.6. Commits `0471e85`..`72ad85f`.

- **B5 — Polimento visual (#92, feito)**:
  - *5a* — X de fechar duplicado na aba Ajuda. Causa: os manuais
    (técnico/leigos) são um `NavigationSplitView` **dentro** da página
    Ajuda, que já tem header com window-controls; os headers internos
    (sidebar + content) mostravam um 2º X. Fix:
    `set_show_start/end_title_buttons(False)` nos dois headers internos
    (`window.py`).
  - *5b* — rail (canto sup. esq.) `"VIGIA"` → `"Vigia Hub"`; header da
    sidebar `"Vigia Suite / Toolkit"` → `"Ferramentas"` (nome legado +
    redundante com o rail). Hub `v0.7.2`.
  - *5c* — **rename global** "Vigia Suite" → em **64 arquivos**, com a
    distinção decidida com o André: **app falando de si** → `Vigia Hub`
    (título da janela, `.desktop Name`, CLI); **coleção/produto** →
    `VigiaOS` (tagline das tools = "parte do VigiaOS", specs, status
    report, docs). Concordância: "da Vigia Suite" → "do VigiaOS". Bulk
    via `perl` article-aware + ajuste à mão dos casos semânticos; testes
    `test_cli`/`test_status` atualizados. Único literal restante = 1
    comentário histórico em `window.py`. Hub `v0.7.3`.
- **B1 — Instalação modular (#88, feito o escopo "hoje")**: cada tool já
  roda isolada (entry-point + `.desktop` + ícone próprios), mas `pip`
  não instala os data-files. Criado **`install/install-tool.sh`**:
  instala UM módulo via `pip --user` (+ `vigia-common`) e registra
  `.desktop` + ícone em `~/.local/share` (espelha os paths do RPM, mas
  user-level, sem root, igual em Silverblue e Workstation). `--list`
  enumera os 16 módulos GUI. README ganhou seção "Instalar só um módulo".
  *Pendente futuro (fora do B1)*: ativar o COPR pro caminho
  `dnf/rpm-ostree install vigia-<tool>` (as specs por-tool já existem).
- **B4 — Pente-fino de redundâncias (#91, feito)**: confirmado na fonte
  (`dashboard/.../processes.py` + `backend.py`) que o **Dashboard v0.2**
  cobre `htop` (aba Processos: CPU/mem, sort, kill, filtro) e `iotop`
  (ordena por I/O read+write **por processo**, lê `/proc/<pid>/io`).
  Ambos **removidos do catálogo** (18→16 pacotes; monitoramento 5→3).
  Ficam `lsof`/`strace` (debug, sem GUI equivalente), `fail2ban`
  (serviço de defesa, não monitor) e `mtr`/`nethogs`/`iftop` (Dashboard
  só mostra banda **por interface**, não por processo/host). Contagens
  stale "~22" espalhadas pelos docs corrigidas pra 16.
- **B3 — Compat Fedora Workstation, runtime (#90, feito)**: novo
  `vigia_common/platform.py` — `is_atomic()` (checa `/run/ostree-booted`),
  `package_manager()`, `needs_reboot_to_apply()` (+6 testes). **Tool
  Installer v0.3.0**: install/uninstall dispatcham `rpm-ostree` (atômico)
  vs `dnf` (Workstation); aba "Pendentes" escondida e mensagens
  adaptadas no Workstation. **Hub v0.7.4**: `ToolEntry.atomic_only` +
  `visible_tools()` escondem o **Deployments Manager** no Workstation;
  instalador de dependência do tray usa `dnf`. Decisões do André:
  esconder Deployments + adaptar o Installer. **Pendente** (não é o
  core do B3): (a) `bootstrap.sh` branch dnf → vai com B2/B6; (b) textos
  de sugestão "rpm-ostree install X" em mensagens de algumas tools
  (antivirus/hardening/file-integrity/rootkit/dns) ainda fixos —
  cosmético, polish futuro (#94).
- **B2 + B6 — Sistema de instalação (#89 + #93, feito)**: reescrito o
  bootstrap como **`install/bootstrap.sh` único que auto-detecta** a
  plataforma (`/run/ostree-booted`) e usa `rpm-ostree` ou `dnf` — em vez
  de dois scripts quase iguais (mais DRY, casa com o espírito do B6).
  Default escolhido pelo André: **instala as 16 tools + backends
  (lynis/clamav/…) + Flatpaks de privacidade, mas NÃO liga serviço
  nenhum** (tor/fail2ban/dnscrypt off — opt-in nas tools = minimum
  surface/LGPD). O `bootstrap.sh` raiz (que só layerava deps ofensivas e
  nem instalava as tools) foi **removido**. Criadas
  `install/silverblue/README.md` + `install/workstation/README.md`
  (guias por plataforma que o B6 pedia) + matriz de compatibilidade no
  README raiz. §8.3 corrigido (URL + descrição batem com o real agora).
  Tool Installer segue útil (extensões + add/remove), só não é mais a
  porta de entrada obrigatória.
- **#94 — Hints de instalação dinâmicos (feito)**: novo
  `vigia_common.platform.install_hint(*pkgs, reboot=)` → `rpm-ostree
  install X && systemctl reboot` (atômico) ou `sudo dnf install X`
  (Workstation). Trocados os 6 hints fixos "rpm-ostree install X" /
  "Em Fedora Silverblue:" em antivirus/file-integrity/hardening (que
  mostravam o comando errado no Workstation). +3 testes; vigia-common
  v0.2.1. Fecha o último pendente do B3.

### 2026-05-30 — Auditoria padrão completa (vistoria + fixes + +30 testes)

Vistoria de 4 dimensões (4 agentes de review em paralelo) + sweep
mecânico. **Veredito**: código "unusually disciplined / remarkably
solid" — zero `shell=True`/`os.system`/`eval`, todo pkexec em argv,
sem vazamento de segredo, zip-slip defendido (backup.py), versões
`pyproject`↔`__init__` alinhadas, sintaxe limpa em todos os `.py`.

**Fixes aplicados**:
- **F1 (HIGH)** `install/bootstrap.sh`: em atômico, `git`/`pip` layered
  só ativam após reboot, mas o script clonava/pip-installava na mesma
  passada → falha no `curl|bash` vanilla. Agora detecta e pede "reboot +
  rode de novo" (2ª passada idempotente).
- **F2 (MED)** PEP 668: `pip install --user` é recusado no Fedora 38+
  sem `--break-system-packages`. `export PIP_BREAK_SYSTEM_PACKAGES=1` nos
  dois scripts de install.
- **F3 (MED)** `dnscrypt_backend.py`: `except (OSError, …, Exception)`
  engolia tudo (mascararia regressão de parse como "sem config") →
  estreitado pra `(OSError, tomllib.TOMLDecodeError)`.
- **F4 (LOW/LGPD)** `browser_extensions.py`: state salvo sem perms →
  agora dir 0700 + arquivo 0600 (consistente com as outras tools).
- **F5 (LOW)** `dashboard/backend.py`: 2 `open()` sem context manager →
  `with`.

**Cobertura nova (+30 testes, 574→604)**: `tests/installer/test_backend.py`
(dispatch rpm-ostree↔dnf no install/uninstall, `_run_pkg_cmd` 7 ramos,
`reboot_system`) + `tests/hub/test_registry.py` (`visible_tools`
atomic_only, `tools_by_category`, métodos de `ToolEntry`). Mock-key:
`backend.py`/`registry.py` importam `is_atomic` no topo → patcha-se
`backend.is_atomic`/`registry.is_atomic`. Bumps: dns v0.4.2, installer
v0.3.1.

**Aceito sem corrigir** (consciente): create-then-chmod TOCTOU sub-ms em
4 writers (LOW, workstation single-user — reescrever arriscaria
regressão); `print()` p/ erro em ~10 sites (cosmético, devia ser
`logging`); `dnf` vs `dnf5` futuro (hoje `dnf` é symlink); mensagem
fire-and-forget do install do tray.

### 2026-05-30 — File Integrity v0.2.2: detecção de movido + hashdeep opcional

Decisão com o André: como o hashdeep estava no catálogo só como CLI e o
programa preza GUI sem terminal, trouxemos o valor dele pra dentro do
**Vigia File Integrity** (em vez de criar um módulo redundante — a tool
já cobre hash/verify/baseline desde o merge do Hash Tools, #68).

- **Detecção de "movido"** na comparação de baseline — **Python puro**,
  pra todos: um arquivo "removido" cujo hash reaparece num "adicionado" =
  movido (`_detect_moves`). Some de added/removed, vira categoria própria
  (badge MOVIDO). É o recurso mais valioso do hashdeep, e nem precisa
  dele.
- **Motor hashdeep opcional** (`use_hashdeep`): toggle na tab Baseline
  (só aparece se hashdeep instalado) — usa hashdeep (C, multi-thread)
  pra hashear mais rápido em árvores grandes; fallback automático pro
  hashlib se ausente/algoritmo não-suportado (sha512) /erro. Hash
  idêntico → engines intercambiáveis, baseline JSON uniforme.
- Tab: header menciona "movido", status conta movidos, render com badge
  accent, nota de engine ("motor: hashdeep"). Registry: `hashdeep` em
  wrapped_packages + features atualizadas.
- **+12 testes** (`tests/integrity/test_hash_baseline.py`): `_detect_moves`
  (move puro / hash diferente / parcial / vazio), integração end-to-end
  (movido + add/rem/mod), seleção de engine (python default, fallback sem
  hashdeep, sha512→python, hashdeep mockado + parse, returncode≠0→fallback,
  filename com vírgula). Suite **604→616**. file-integrity v0.2.2.
- **Fix (teste do André na VM)**: `rpm-ostree install hashdeep` falhava
  com "Packages not found" — o **pacote** no Fedora é **`md5deep`** (a
  suite md5deep/sha256deep/hashdeep; o **binário** é `hashdeep`).
  Corrigido o `package` no `catalog.py` (md5deep; `binary`/detecção
  seguem `hashdeep`, que está correto) + `bootstrap.sh`. installer
  v0.3.2. *Lição: nome-de-pacote ≠ nome-de-binário só pega em teste real
  de repo — análise estática no mac não alcança.*

### 2026-05-30 — Dashboard v0.3.0: inspetor de processo (strace -c)

A pedido do André (o `strace` estava no catálogo só como CLI; o programa
preza GUI sem terminal). Em vez de módulo novo redundante, a feature
entrou no **Dashboard** (que já lista processos): botão **"Inspecionar"**
por processo → roda `pkexec timeout -s INT 5 strace -f -c -p <pid>` e
mostra o resumo de syscalls (tabela por %tempo) num diálogo. Read-only.

- `proc_inspect.py`: `strace_installed`, `inspect_process_blocking`,
  `parse_strace_summary` (robusto a versões — ignora cabeçalho/separador/
  linha "total", recalcula total das rows, ordena por %tempo). **Não** se
  chama `inspect.py` (colidiria com a stdlib).
- **pkexec** porque ptrace de processo alheio exige root (yama
  ptrace_scope=1) e ler syscalls é sensível (LGPD). Botão só aparece se
  `strace` instalado.
- `processes.py`: botão na linha de Ações + diálogo de confirmação +
  worker thread + resultado em `AlertDialog` com tabela (top 20).
- **+11 testes** (parser + dispatch mockado, sem precisar de strace/root).
  Suite 616→627. Dashboard v0.3.0; `strace` em wrapped_packages.
- Doc-sync: badges de versão do README sincronizados (hub/file-integrity/
  tool-installer/dns/dashboard estavam stale dos commits do dia).
- **v0.3.1 (fix, reportado pelo André)**: a aba Processos reconstruía a
  lista inteira a cada 2s, colapsando a linha que o usuário acabara de
  expandir ("abre e fecha" — e sumia com o botão Inspecionar antes do
  clique). Bug pré-existente, virou bloqueante com o inspetor. Fix:
  `_refresh()` pula o rebuild enquanto `_any_expanded()` (linha aberta);
  retoma quando tudo fecha.
- **v0.3.2 (fix de locale, reportado pelo André)**: o inspetor dava
  "Sem dados de syscall" no Fedora pt-BR. Causa: `strace -c` imprime os
  floats com **vírgula** decimal (`100,00`) no locale pt-BR, e
  `float("100,00")` estoura → todas as rows descartadas. Fix duplo:
  rodar o strace via `pkexec env LC_ALL=C …` (força ponto; pkexec
  sanitiza env, daí o `env` explícito) + parser troca `,`→`.` antes do
  `float`. *Lição geral: subprocess cujo output tem número formatado
  deve rodar com `LC_ALL=C` — só pega em sistema com locale não-inglês.*

### 2026-05-30 — Monitor do Sistema v0.4.0: rename + aba Rede (nethogs)

Decisão de UX com o André: o Dashboard **é** a ferramenta de
monitoramento, então (1) renomeado **"Dashboard" → "Monitor do Sistema"**
(nome visível; `id`/módulo/pacote `dashboard`/`vigia_dashboard`/
`br.com.vigia.Dashboard` seguem iguais) e (2) ganhou uma aba **Rede**.
Decidimos **não** dividir em dois módulos (evitaria "Monitoramento ›
Monitoramento" + fragmentação) e **não** mover Alertas pro Config do Hub
(quebraria o standalone — Alertas é monitoramento ativo). Commits
`046507e`..`853a4c2`.

- **Aba Rede — banda por processo** (`net_bandwidth.py` + `tabs/network.py`):
  fecha a lacuna que o próprio código admitia ("Bytes/s por PID = futuro/
  eBPF"). Botão "Medir banda" → snapshot `pkexec env LC_ALL=C nethogs -t
  -c 4 -d 1` (~4s, read-only, lazy) → tabela ↑/↓ por processo. Acha
  exfiltração ("que processo manda dados pra fora?").
- **Parser ajustado ao output REAL** (teste do André na VM): o campo do
  `nethogs -t` é `caminho/pid/uid` quando atribui, mas a própria
  **conexão** (`local-remoto`) com pid 0 quando NÃO consegue (conexão
  pré-existente que ele não viu nascer). Não-atribuídos aparecem pelo
  **endpoint remoto** (não somem). `LC_ALL=C` (lição do strace) + tolera
  vírgula. Validado: firefox atribuído com PID + conexões soltas por
  endpoint.
- **iftop removido do catálogo** (16→15 pkgs): banda por conexão já é
  coberta pelas linhas não-atribuídas da aba Rede → iftop redundante.
  nethogs fica (é o backend). Tool Installer v0.3.3.
- +12 testes do parser nethogs (incl. o output real travado como
  regressão). Manuais leigo+técnico documentam a aba Rede + o inspetor
  strace. Suite 643.

### 2026-05-30 — Monitor do Sistema v0.4.1: selo de plataforma no hero

Polimento de UX sugerido pelo André: o título grande do hero da Visão
Geral era o **hostname** (`info.hostname`) — que numa instalação vanilla é
o default `fedora`, sem valor. O que importa pro produto é a **plataforma**
(Silverblue/atômico vs Workstation), porque o comportamento muda
(`rpm-ostree` vs `dnf`, Deployments só no atômico). Avaliamos 2 designs
(título = plataforma **vs** hostname + selo); o André escolheu o **selo**.

- **Selo colorido** abaixo do hostname (mantém a identidade da máquina):
  pill **verde** (`@success_bg_color`) p/ atômico-Silverblue, **azul**
  (`@accent_bg_color`) p/ Workstation. Cor já grita qual sistema é. CSS
  theme-aware via `Gtk.CssProvider` carregado 1x (`_ensure_platform_css`,
  guard `load_from_string` GTK≥4.12 com fallback).
- **`backend.get_platform_label() -> (str, bool)`** (cacheado): lê
  `NAME`/`VARIANT` de `/etc/os-release` (`'Fedora Linux'→'Fedora'`,
  `'Workstation Edition'→'Workstation'`) + `is_atomic()` p/ o qualificador
  (`atômico`/`tradicional`, alinhado ao `bootstrap.sh`). Parser puro
  `_parse_platform(text, atomic)` — testável sem GTK/root.
- Subtítulo agora **tira o `(Silverblue)`** redundante do `PRETTY_NAME`
  (a variante já está no selo): `info.distro.split(" (")[0]`.
- +12 testes (`test_platform_label.py`: Silverblue/Workstation/Kinoite,
  strip de `Edition`, fallback sem os-release, cache). Manuais leigo+técnico
  atualizados. Suite **655** (+12).

### 2026-05-30 — Remoção do Tor de sistema (Tor Browser vira único caminho)

Pente-fino do catálogo com o André: `tor` (daemon) + `torsocks` (wrapper
CLI) saíram. Raciocínio: o **Tor Browser** (Flatpak `torbrowser-launcher`,
já no bootstrap) traz o **próprio** tor embutido (porta isolada ~9150) e é o
caminho seguro/leigo de navegação anônima. O `tor` de **sistema** (porta
9050) servia só pra rotear *outros* apps — cenário power-user que dependia
justamente do `torsocks`, terminal-only (público é sem-terminal). E o toggle
"Serviço Tor" do Privacy Controls passava **falsa sensação de segurança**
(ligar o daemon ≠ navegador anônimo). Decisão: Tor Browser como único Tor.

- **Privacy Controls v0.3.2**: removido o toggle `TOR` (`systemd_toggles.py`
  + `ALL_TOGGLES`); a categoria *Anonimização* sumiu (**13→12 toggles**,
  8→7 categorias, 3→2 system-scope). `import shutil` órfão removido; notas
  no Sobre + docstring do `extra_available_check` (hook genérico, mantido).
- **Tool Installer v0.3.4**: `tor` + `torsocks` fora do `catalog.py`
  (**15→13 pacotes**); descrição da categoria *privacidade* sem "Tor".
- **bootstrap.sh**: `tor torsocks` fora do `DEPS_BACKENDS`; hints de "serviços
  off" sem tor. Tor Browser (Flatpak) **permanece**.
- **Mantido de propósito**: Tor Browser (Flatpak); booleanos SELinux `tor_*`
  (política do kernel, independem do pacote); analogia "similar ao Tor" do
  DNS Manager.
- +7 testes (`test_catalog.py`: tor/torsocks ausentes, lock de 13 pacotes).
  Manuais + READMEs + spec + registry sincronizados (incl. drift do iftop:
  16→13). Suite **662**.

### 2026-05-30 — `wireguard-tools` removido (VPN fica com NetworkManager / app)

Pente-fino do catálogo, parte 2. O André (e o público advogado) usa VPN
**comercial** (NordVPN-style). Pra esse caso o `wireguard-tools` (`wg`/
`wg-quick`) não serve: o app do provedor traz a própria stack (NordLynx) e o
caminho no-terminal na Silverblue é importar o `.conf`/`.ovpn` no
**NetworkManager** (GNOME Settings → Rede → VPN), que já tem WireGuard
embutido e **não precisa** do pacote. O próprio `why` da entrada já admitia
"NM importa e gerencia nativamente, sem tool dedicada" — mesma razão da
remoção do VPN Manager.

- **Tool Installer v0.3.5**: `wireguard-tools` fora do `catalog.py`
  (**13→12 pacotes**); categoria *privacidade* = só `dnscrypt-proxy`,
  descrição sem "VPN". Fora do `bootstrap.sh` também.
- `test_catalog.py` atualizado (lock 12, wireguard ausente). Manuais +
  README + DEVELOPMENT sincronizados. Suite **662**.
- **Mantido**: menção a "wireguard" no Capabilities Inspector (exemplo de uso
  de capability, não o pacote).
- **+ v0.3.6 (mesmo dia)**: adicionado `NetworkManager-openvpn-gnome` ao
  catálogo (opt-in, **12→13 pacotes**) como o enabler certo do caminho
  no-terminal — importar `.ovpn` (NordVPN/Proton/Mullvad) em GNOME Settings →
  Rede → VPN e ligar pela barra. Troca uma CLI que o público não usa por uma
  GUI que usa. Fica no catálogo (opt-in), **não** no bootstrap.

### 2026-05-31 — Reports v0.2.0: overhaul visual (gráficos SVG + resumo + status)

Pedido do André: deixar o relatório gerado mais bonito e fácil pro usuário
médio. Mantida a filosofia "stack leve" (HTML + imprimir→PDF do navegador,
**sem** WeasyPrint). Quatro frentes:

- **Gráficos SVG nativos** (`charts.py`, novo): `bar_chart` (falhas por dia),
  `hbar_chart` (top IPs banidos / usuários sudo) e `donut` (aceitos ×
  falhados). SVG inline gerado em Python — **sem JS, sem CDN, sem rede**
  (offline/LGPD), vetorial no print, **zero dependência nova**. Registrados
  como globals do Jinja em `renderer._make_env()`; dado do usuário escapado.
- **Resumo executivo + selo de status** (`backend.build_status` /
  `build_summary` / `events_by_day`): parágrafo em pt-BR + selo 🟢/🟡/🔴 por
  heurística honesta (`danger` = sucesso SSH em meio a ≥50 falhas; `warn` =
  ≥20 falhas ou algum ban). Renderizados no `base.html` pros 2 modelos
  automaticamente.
- **Tipografia/layout**: stack de fonte refinado (`tabular-nums` nos KPIs),
  cabeçalho com selo, caixa de resumo, cards de gráfico, zebra nas tabelas e
  CSS de impressão (A4, page-breaks, `print-color-adjust`).
- **+28 testes** (`test_charts.py`, `test_summary.py` e o `test_render.py` —
  smoke de render ponta-a-ponta que **não existia**). Corrigido o drift do
  badge (dizia "Jinja2 + WeasyPrint", mas WeasyPrint nunca foi ligado →
  "Jinja2 + SVG"). Suite **690**. *Próximo (sugerido): novos modelos —
  Resumo Executivo 1-página, Acesso Administrativo.*

### 2026-05-31 — Reports v0.2.1: +2 modelos (Resumo Executivo, Acesso Administrativo)

Frente 4 do overhaul (os "novos modelos" sugeridos acima), ambos a partir dos
dados **já coletados** — zero coletor novo de sistema:

- **Resumo Executivo** (`executive_summary`): 1 página visual — reaproveita o
  `activity_overview` + `build_highlights()` (bullets concretos), **sem** as
  tabelas longas de evento. Pra entregar a cliente/auditor.
- **Acesso Administrativo** (`admin_access`): trilha de `sudo`+`pkexec` — quem
  rodou comando de root, quando. `top_admin_users` + `admin_by_day` + selo por
  nº de admins (`build_admin_status`: ≥2 → *warn* com nota LGPD do menor
  privilégio); texto via `build_admin_summary`.
- Registrados em `renderer.TEMPLATES` + dispatch no `generate.py` (o combo da UI
  lista **4** modelos agora). +8 testes (highlights, admin status/resumo,
  render dos 2). Manuais + registry + README. Suite **698**.

### 2026-05-31 — Reports v0.2.2: modelo Conformidade LGPD (1º consolidado)

Primeiro dos "relatórios consolidados" pedidos pelo André — e o documento mais
valioso pro escritório (prova de medidas técnicas, LGPD art. 46).

- **`compliance.py`** (novo): 9 checagens de postura **user-readable** (sem
  pkexec) — firewall, disco LUKS, SELinux, SSH, DNS encriptado, fail2ban,
  telemetria, localização, lock screen. Interpretação em funções puras
  (`_state_service/_selinux/_gsettings/_disk`) + `compliance_score/status/
  summary`. `status` = *danger* se item **crítico** (firewall/disco) falha.
  Degrada com elegância: backend ausente → *não aplicável* (não conta no índice).
- **`collect_for_lgpd_compliance`** + `lgpd_compliance.html`: KPIs (X/N + %),
  rosca conforme×pendente, tabela com cada medida + tag de estado + "por que
  importa" + marcador *crítico*. É o modelo nº **5** no combo da UI.
- +14 testes (`test_compliance.py`: interpretadores/score/status/smoke +
  render). Manuais + registry + README. Suite **712**.
- **Próxima etapa (consolidados, parte 2):** *Saúde do Sistema* — juntar Lynis
  + AIDE + ClamAV + Rootkit num doc. Fontes user-readable já mapeadas:
  `~/.config/vigia/file-integrity.json`, `~/.local/share/vigia-antivirus/
  scan-*.json`, `~/.local/share/vigia-rootkit/scans/*.json` (a do Lynis/
  hardening-checks ainda a confirmar — talvez exija modo admin pra ler
  `/var/log/lynis-report.dat`).

### 2026-05-31 — Reports v0.2.3: modelo Saúde do Sistema (consolidados, parte 2)

Segundo (e último planejado) dos consolidados — fecha a frente "documentar
tudo": um doc que junta o estado das **4 defesas** da suíte.

- **`system_health.py`** (novo): lê o **último resultado** que cada tool
  persistiu, **sem importar o código delas** (Reports desacoplado — só lê
  arquivo): Lynis (`/var/log/lynis-report.dat` → `hardening_index`, legível
  pós-chown do Hardening), ClamAV (`scan-*.json` → `infected_files`), AIDE
  (`file-integrity.json` → `last_check`), rootkits (`scans/*.json` →
  `infected_count`). Cada defesa → `{state: ok/warn/danger/missing, headline,
  ran_at}`; tool nunca rodada = *missing* (não conta no score). Interpretadores
  puros (`_interpret_*`) testáveis sem I/O.
- **`collect_for_system_health`** + `system_health.html`: KPIs (saudáveis /
  atenção / não-executadas), rosca de panorama, tabela defesa×estado×resultado
  ×data. Modelo nº **6** no combo.
- +21 testes (`test_system_health.py` + render). Suite **733**.

Com isso os 2 consolidados pedidos pelo André estão **prontos**. Próximas
ideias da frente "documentação" (quando quiser): 🥇 agendamento automático
(timer systemd + modo headless) e 🥉 selo de integridade (SHA-256) + pacote de
auditoria `.zip`.

### 2026-05-31 — Reports v0.2.4: selo de integridade SHA-256 + pacote de auditoria

A frente 🥉 — dá **valor de prova** aos documentos (anti-adulteração, LGPD).

- **Selo no rodapé** (`renderer._doc_seal`): SHA-256 de `json.dumps(ctx,
  sort_keys, default=str)` (dados+meta, único por geração). Exibido no
  `base.html`. Fingerprint **visível** do conteúdo.
- **Sidecar `.sha256`** (`write_report`): `<rel>.html.sha256` no formato
  `sha256sum`. Como `write_text(utf-8)` grava exatamente `html.encode()`, o
  digest **bate com `sha256sum <file>`** → verificação **independente** com
  `sha256sum -c` (validado: `shasum -c` → `OK` no arquivo real). É a prova de
  adulteração de verdade.
- **Pacote de auditoria** (`build_audit_package`): zipa `.html` + `.sha256` +
  `MANIFEST.txt` (hashes) + `LEIA-ME.txt` (passo a passo) → `auditoria-<ts>.zip`
  (0600). Botão na aba **Biblioteca** (`Adw.AlertDialog` → abrir pasta).
- +10 testes (`test_integrity.py`: selo determinístico, sidecar == hash do
  arquivo, zip com manifesto/sidecars). Manuais + registry + README. Suite
  **743**.

---

## 10. Roadmap

### 10.1 Próximas iterações por ferramenta

**Vigia Hub v0.6+**:
- Status indicators mais ricos (versão instalada de cada tool)
- Settings global (tema, fonte, autostart de algumas tools)
- Notificações desktop quando tools terminam tarefas longas

**Activity Log v0.8+**:
- Empacotamento RPM via COPR (spec pronto, falta criar conta COPR + push)
- Modo `--watch <pattern>`: alerta quando padrão específico aparece
- Integração com inotify para refresh sub-segundo

**Privacy Controls v0.4+**:
- D-Bus helper + polkit policy `auth_admin_keep` (cache 5min)
- Toggles novos: screen lock timeout custom, camera/mic per-app
- Profiles: "Modo Paranóia" (todos OFF), "Modo Confiança" (padrão), "Modo Custom"

**SELinux Manager v0.3+**:
- Adicionar/remover ports (atualmente só read-only)
- File contexts customizados (`semanage fcontext`)
- Compilar+instalar policy do audit2allow com 1 botão
- Login mappings, user contexts (tabs novas)

**Firewall Manager v0.2+**:
- Rich rules editor (rate-limit, log action, family=ipv6)
- ICMP block / masquerade / port-forwarding
- Profile presets ("Trabalho", "Público", "Paranóia")
- Service editor (criar service custom)

**Network Monitor v0.2+**:
- DNS reverse lookup opcional (async em background)
- Bandwidth por processo via `nethogs`
- Históricos curtos (5min back), gráficos de throughput
- Filtros pré-definidos
- Integração com Firewall ("bloquear esse IP") e Activity Log

**Hardening Checks v0.2+**:
- Comparativos entre runs (delta findings)
- Export para PDF (via Reports)
- Schedule de runs periódicas (systemd timer)

**Reports v0.2+**:
- Templates customizados pelo usuário
- Agendamento de relatórios (semanal/mensal automático)
- Assinatura digital opcional dos PDFs (GPG)

**File Integrity v0.2+**:
- Notificação desktop quando check encontra diffs
- Schedule automático (systemd timer)
- Comparativo visual entre snapshots históricos

**Tool Installer v0.2+**:
- Pesquisa fuzzy no catálogo
- "Bundles" pré-definidos (Network Pro, Forensics Starter, etc.)
- Status: "Instalado / Pendente / Disponível" por entry

**DNS Manager v0.5+** (backend já é `dnscrypt-proxy` desde a v0.4.1 — DoH +
DNSCrypt + DNSSEC, 3 abas Status/Provedores/Sobre):
- **Blocklists locais** (Pi-hole-like) opcionais — `.txt` linha-por-linha
  (`doubleclick.net`, `googletagmanager.com`, …) para bloquear tracking
  corporate sem rodar Pi-hole em hardware separado. Existiram nas v0.2-v0.3,
  removidas na v0.4.0 por complexidade; podem voltar como opt-in.
- **Anonymized DNS**: relay servers entre user e resolver — esconde o IP
  do user do resolver final (~Tor-light para DNS). Útil para LGPD-paranoia.
- **Stats**: queries answered / blocked / cached, estilo Pi-hole mini
  (também removidas na v0.4.0; voltariam junto das blocklists).

**Capabilities Inspector v0.2+**:
- Modificação de capabilities (`setcap`) com confirmação forte
- Comparativo "expected vs actual" baseado em policy
- Export findings para Activity Log

**Dashboard v0.2+** (próximas features priorizadas):

*Top-priority (curtos, alto valor)*:
- **Alertas configuráveis**: limiar por métrica (CPU > 95% por 1min,
  RAM > 90%, disco > 95%, temp > 85°C) → notificação desktop via
  `Gio.Notification`. Configuração em `~/.config/vigia/dashboard.json`.
  Threshold + duração mínima + cooldown entre alerts.
- **Per-process I/O**: implementar leitura de `/proc/<pid>/io`
  (read_bytes, write_bytes). Cumulativo desde início do processo.
  Calcular delta vs leitura anterior → MB/s por PID. Coluna nova na
  tab Processos. Substitui `iotop` GUI-side.
- **Per-process bandwidth**: parsing de `/proc/net/tcp6?` + `/proc/<pid>/fd/*`
  → quais sockets pertencem a qual PID. Subscribe netlink `NETLINK_INET_DIAG`
  para refresh sem rescan completo. Substitui `nethogs` GUI-side.

*Medium-priority (médios, qualidade visual)*:
- **Gráfico de barras CPU per-core**: alternativa à linha sobreposta
  (que pode ficar bagunçada com 16+ cores). Toggle "linha / barra"
  na aba Recursos.
- **Top processes na sparkline**: ao passar mouse na sparkline da
  Visão Geral, mostra qual processo subiu o pico (tooltip).
- **Disk I/O histograma**: além da linha de read/write, mostrar
  histograma de latency (p50/p95/p99) por device. Lê `/proc/diskstats`
  campos 7-10 (read/write completion times).
- **Network: filtro por interface**: dropdown "Todas / eth0 / wg0 / lo"
  na aba Recursos. Útil pra isolar VPN vs LAN.

*Lower-priority (longos, infra)*:
- **Persistência histórica**: SQLite em `~/.local/share/vigia-dashboard/`
  com aggregates rolling (1min, 5min, 1h, 1d). Aba nova "Histórico"
  com seletor de janela temporal.
- **GPU monitoring**: NVIDIA via `nvidia-smi --query-gpu=... --format=csv`
  (já é JSON-ish), AMD via `/sys/class/drm/card0/device/`. Card opcional
  na Visão Geral se detectado.
- **Snapshot export**: botão "Capturar snapshot" gera JSON + PNG
  do estado atual. Útil pra anexar em ticket de suporte ou relatório
  Vigia Reports.
- **Refresh rate configurável**: slider na Visão Geral (0.5s / 1s /
  2s / 5s). Trade-off CPU usage vs responsividade.
- **Tema de cores customizável**: usuário escolhe paleta (semantic
  default, monochrome emerald, high-contrast). Salva em config.

### 10.2 Ferramentas novas planejadas (post-v0.1)

**Antivirus** — IMPLEMENTADO no ciclo 2026-05-25 (security toolkit); roadmap
em §10.1 acima. Network Scanner, Firmware Analyzer e Hash Tools nasceram no
mesmo ciclo mas foram removidos/mergeados depois (ver §2 e a lista de
"Removidas" na §1) — só o Antivirus permanece.

**Vigia Container Audit** (v0.5 alvo):
- Audit de containers Podman/Docker rodando
- Detecta containers privilegiados, com mounts sensíveis, com caps adicionais
- Stack: Python + GTK4 + `podman ps --format json`

**Vigia Sandbox Manager** (v0.5 alvo):
- Wrap de Bubblewrap / Flatpak sandbox para rodar binários suspeitos
- "Run in sandbox" — UI que mostra o que o programa tentou acessar
- Stack: Python + GTK4 + `bwrap` + strace/seccomp logs

**Vigia GPG Manager** (v0.5 alvo):
- Wrap de `gpg --list-keys` + sign + verify
- Geração de chaves com defaults seguros (ed25519)
- Integração com SentinelBR password manager (futuro)
- Stack: Python + GTK4

**Vigia Disk Encryption** (v1.0 alvo):
- Manage LUKS volumes + headers backup
- Senha master + recovery keys
- Stack: Python + GTK4 + `cryptsetup`

### 10.3 Empacotamento e distribuição (meta-trabalho)

- **COPR project `andre28abr/vigia`**: criar conta + projeto + webhook SCM
- Spec files RPM para TODAS as 13 ferramentas (já tem Activity Log core)
- Bootstrap completo: depois de COPR ativo, usuário roda 1 comando para ter
  toda a suite via `rpm-ostree install vigia-suite` (metapackage)
- **AppStream metadata** (`.appdata.xml`) para integração com GNOME Software

### 10.4 Refatorações técnicas pendentes

- **`vigia_common` shared package**: extrair `_helpers.py` duplicado entre
  9 tools (~600 linhas duplicadas) + `markdown.py` do Hub ✅ feito
- **D-Bus service compartilhado** com polkit policy `auth_admin_keep` para
  evitar polkit dialog repetitivo em ops batch
- **Padrão de pkexec + tratamento de "Request dismissed"** abstrair em
  helper único
- **Testes**: adicionar `pytest` para backends Python ✅ feito (262 tests)

### 10.5 Ecossistema Vigia — produtos futuros (longo prazo)

Definido em 2026-05-27. Em vez de inflar VigiaOS com features fora do
escopo (multi-host, pentest), separar em **4 produtos distintos**
compartilhando UI + `vigia-common` lib.

| Produto | Audiência | Escopo | Status |
|---------|-----------|--------|--------|
| **VigiaOS** | Advogado, escritório LGPD | Single-host audit/privacy/hardening | ✅ Atual (16 tools) |
| **VigiaOps** | Sysadmin, MSP, gestor TI | SSH multi-host orchestration | 📌 Próximo após v1.0 |
| **VigiaRed** | Pentester, red team | Ferramentas ofensivas com GUI | 🔮 Futuro |
| **VigiaBlue** | Blue team, SOC analyst | SIEM-lite, detection, response | 🔮 Futuro |

**VigiaOps** absorve a ideia inicial de "SSH multi-host management via
Hub". Separado pra não conflitar com posicionamento atual LGPD/desktop.
Features-alvo: inventory de hosts, SSH connection pool, command runner
remoto com streaming, multi-host fan-out, integration com tools VigiaOS
rodando remoto, audit log assinado.

**VigiaRed** poderia trazer de volta **Network Scanner (nmap)** e
**Firmware Analyzer (binwalk)** que removemos do VigiaOS — naquela
audiência fazem sentido. Em **2026-05-29** os próprios pacotes `nmap`,
`tcpdump` e `binwalk` saíram também do catálogo do Tool Installer pelo
mesmo motivo (recon/sniffing/RE = perfil ofensivo), ficando reservados
pra cá. Mais possíveis: vuln scanner (nuclei), web scanner (zap),
exploitation (metasploit lite), OSINT.

**VigiaBlue** estende **Activity Log core (Rust)** com correlation
distribuída, log aggregation, threat intel feeds (MISP, OTX), YARA,
memory forensics.

**Estratégia compartilhada entre os 4**:

1. `vigia-common` Python package (helpers GTK4)
2. Identidade visual (zinc-950 + emerald)
3. Padrão de tabs (Adw.ViewStack + ToolbarView)
4. Estrutura monorepo (`tools/<nome>/`)
5. RPM packaging via COPR
6. Privacy/LGPD baseline (chmod 0600, dialogs claros)

**Quando revisitar**: após VigiaOS estar em v1.0 (estável, COPR ativo,
~6 meses de uso). Começar por **VigiaOps** — interesse imediato.

### 10.6 Backlog priorizado — próxima sessão (planejado 2026-05-30)

> Levantado com o André em 2026-05-29. Cada item já vem com o que o
> código faz **hoje** (verificado na fonte) + o que falta + decisões a
> tomar. Itens B1–B5 = tasks #88–#92.

**Modelo conceitual confirmado** (norteia B5): **VigiaOS** é o
*ecossistema* (este monorepo / toolkit). **Vigia Hub** é *este app* (o
launcher central). **Vigia Red / Blue / Ops** serão apps *irmãos* dentro
do mesmo ecossistema. Logo "Vigia Suite" é nome legado a aposentar em
favor de "Vigia Hub" (app) + "VigiaOS" (ecossistema).

#### B1 — Instalação modular (rodar 1 tool isolada) — #88 ✅ (ver §9 2026-05-30)

André: o Hub é o switch completo, mas às vezes o user quer só **um
módulo** (ex: só o Antivírus) — aparece no GNOME com ícone próprio,
clica, roda isolado.

- **Hoje**: tecnicamente **já funciona**. Cada tool tem entry-point
  próprio (`vigia-antivirus`, `vigia-dns`, …) e `.desktop` próprio
  (`br.com.vigia.Antivirus.desktop`, `Exec=vigia-antivirus`,
  `Icon=br.com.vigia.Antivirus`). Todas dependem de `vigia-common`.
- **Falta**: (a) **unidade de distribuição** instalável sozinha — há
  specs RPM por tool (COPR), validar que 1 RPM/tool resolve dep de
  `vigia-common`; (b) **documentar** o fluxo "instale só o módulo X"
  (leigo + técnico); (c) garantir que o `.desktop` + ícone de cada tool
  é instalado mesmo sem o Hub.
- **Decisão**: a doc descreve instalar via RPM por tool (COPR) ou via
  `pip install -e tools/<tool>`? Definir o caminho oficial pro user.

#### B2 — First-run instala todas as deps (repensar o Installer) — #89 ✅ (ver §9 2026-05-30)

André: ao instalar pela 1ª vez, já instalar **todos** os pacotes que o
Hub precisa. Aí o Tool Installer fica meio desnecessário. Talvez um
shell script que roda **antes**: atualiza o sistema + instala tudo.

- **Hoje**: `bootstrap.sh` **já layerа RPMs + Flatpaks**, MAS:
  1. **Dessincronizado** — ainda inclui `nmap`, `tcpdump`, `binwalk`,
     `yara`, `wireshark-cli`, `nmap-ncat` (perfil ofensivo que tiramos
     do escopo em 2026-05-29 → VigiaRed). Precisa enxugar pra bater com
     o catálogo defensivo (18 pkgs).
  2. **Não instala os tools Vigia em si** — não clona repo, não roda
     `pip install`, não cria symlinks/.desktop. Só prepara dependências.
  3. **Drift no §8.3**: a descrição que ajustei em 2026-05-29 ("clona
     repo + pip installs + symlinks + .desktop") **não corresponde** ao
     `bootstrap.sh` real — corrigir um dos dois (provavelmente fazer o
     script realmente instalar os tools, e então a doc fica correta).
- **Falta / trabalho**: reescrever `bootstrap.sh` → (1) `update`;
  (2) instalar só deps do catálogo enxuto; (3) instalar os tools Vigia;
  (4) criar `.desktop`/ícones. Repensar o **papel do Tool Installer**:
  se tudo já vem, ele vira gerenciador *opcional* (add/remove) e não
  porta de entrada obrigatória.
- **Tensão a resolver**: instalar TUDO de cara contraria o princípio
  **minimum surface area** (LGPD/escritório — abrir só o necessário).
  Provável meio-termo: instalar deps das tools *core*, mas serviços
  (fail2ban, dnscrypt-proxy) ficam **opt-in** via Installer.

#### B3 — Compatibilidade Fedora Workstation (não-atômico) — #90 ✅ runtime (ver §9 2026-05-30; bootstrap dnf fica no B2/B6)

André: verificar se o Hub roda também no **Fedora Workstation
tradicional** (dnf), e fazer o mesmo script de instalação.

- **Hoje**: **atomic-only**. `bootstrap.sh` faz `exit 1` se não achar
  `rpm-ostree`. **24 arquivos .py** chamam `rpm-ostree`. **Não existe
  detecção de distro** em lugar nenhum.
- **Bloqueios reais**: **Deployments Manager** é intrinsecamente
  atômico (deployments rpm-ostree não existem no Workstation). Tool
  Installer usa `pkexec rpm-ostree install` (+ reboot) — no Workstation
  seria `dnf install` (sem reboot, sem tab Pendentes).
- **Trabalho**: (a) helper `is_atomic()` em `vigia-common` (checar
  `/run/ostree-booted` ou presença de `rpm-ostree`); (b) abstrair o
  backend de install (rpm-ostree ↔ dnf); (c) esconder/adaptar tools
  atomic-only no Workstation (Deployments; tab Pendentes do Installer);
  (d) branch `dnf` no `bootstrap.sh`. **Item substancial** — escopo
  grande, fazer por etapas.

#### B4 — Pente-fino de redundâncias (Dashboard ↔ catálogo) — #91 ✅ (ver §9 2026-05-30)

André: revisar features/pacotes a manter ou retirar. Ex: o **Dashboard**
já mostra monitor de sistema com processos — alguns pacotes de monitor
podem ser redundantes. "Verificar com calma."

- **Hoje**: catálogo *monitoramento* = `htop`, `iotop`, `lsof`,
  `strace`, `fail2ban`. O **Dashboard** já cobre processos, I/O,
  conexões, CPU/mem em GUI nativa — e as próprias descrições de
  `htop`/`iotop` no catálogo **já dizem** "alternativa GUI: Vigia
  Dashboard".
- **A auditar**: `htop`/`iotop` redundantes com o Dashboard?
  `lsof`/`strace` são debug pontual (provável manter). Mapear
  sobreposição e decidir o que sai. **Sem ação imediata** — análise.

#### B5 — Polimento visual (3 sub-itens) — #92 ✅ (ver §9 2026-05-30)

- **5a · X de fechar duplicado na Ajuda (Markdown)**: tirar o X do
  visualizador, deixar só o da janela do Hub (que minimiza/fecha
  conforme config de tray). **Suspeito**: `_wrap_with_header`
  (`window.py:629`) e os headers das abas Ajuda/Configurações criam
  `Adw.HeaderBar` com window-controls próprios, somados ao X da janela.
  **Fix provável**: `header.set_show_end_title_buttons(False)` nos
  headers internos. *Confirmar qual header gera o X extra.*
- **5b · Header da sidebar**: hoje `Adw.WindowTitle(title="Vigia Suite",
  subtitle="Toolkit")` (`window.py:1415`). → título **"Vigia Hub"**;
  subtítulo "Toolkit" → **remover ou substituir** (sugestão: "VigiaOS").
- **5c · Rename "Vigia Suite" → "Vigia Hub"**: aparece em MUITOS
  lugares — `window.py` (108, 324, 1399, 1415, 1456), `.desktop`
  (`Name=Vigia Suite`), descrições de `pyproject` e READMEs ("parte da
  Vigia Suite"). **Decisão**: rename global ou só strings visíveis do
  app? E a tagline "parte da Vigia Suite" das 16 tools vira "parte do
  **VigiaOS**"? *Recomendação a confirmar*: app visível = "Vigia Hub";
  subtítulo = "VigiaOS"; tagline das tools = "parte do VigiaOS".

#### B6 — Organização do repo: separação por plataforma SEM duplicar código — #93 ✅ (feito como 1 bootstrap auto-detect + READMEs por plataforma; ver §9 2026-05-30)

**Decidido com o André em 2026-05-29** (não é mais pergunta aberta).
Motivação dele: o usuário precisa **entender de relance** o que roda no
sistema dele (Silverblue vs Workstation) e como instalar só uma peça.

**Decisão**: a separação é **visual/de instalação**, não de código.
Código fica **único e DRY** — nada de duas árvores-mestre duplicadas
(duplicar significaria todo bug-fix 2× + drift; a única diferença real
entre plataformas é o backend de install, resolvido em runtime por B3).

Estrutura-alvo:

```
VigiaOS/                       ← repo = ecossistema
├── README.md                 ← visão geral + MATRIZ de compat (✅/⚠️/❌) + ecossistema
├── install/
│   ├── silverblue/           ← bootstrap.sh (rpm-ostree) + README (guia + instalar 1 módulo)
│   └── workstation/          ← bootstrap.sh (dnf) + README
├── tools/                    ← CÓDIGO, uma cópia só (vigia-common + 16 tools)
├── docs/  └─ packaging/
```

**Trabalho**:
- Mover o `bootstrap.sh` atual → `install/silverblue/bootstrap.sh`;
  criar `install/workstation/bootstrap.sh` (branch dnf — depende de B3).
  Atualizar a URL `curl` do bootstrap nos docs (raiz → `install/...`).
- README de cada plataforma: lista os produtos/módulos + como instalar
  **um só** (conecta com B1).
- README raiz: **matriz de compatibilidade** (tool × Silverblue/Workstation)
  + seção do **ecossistema** (VigiaOS hoje; VigiaRed/VigiaBlue reservados).
- README por módulo orientando instalação separada (conecta com B1).
- **Produtos futuros (Red/Blue)**: **NÃO** criar pastas vazias agora —
  só sinalizar no README; cria a estrutura quando o produto começar.
  **Tudo no mesmo repo** (decisão do André).

**Dependências**: precisa de **B3** (`is_atomic()` + abstração
rpm-ostree↔dnf) pros dois bootstraps fazerem sentido. Casa com **B1**
(instalar módulo isolado) e **B2** (conteúdo dos bootstraps). Ordem
sugerida revisada: **B5 → B1 → (B3 ⇒ B2 ⇒ B6) → B4**.

---

## 11. Lições aprendidas

### 11.1 Pivot v1 → v2 valeu a pena
Custo de manter image build era alto demais para retorno. Ferramentas
individuais são muito mais sustentáveis. Cada uma resolve um problema concreto.

### 11.2 Python + GTK4 + libadwaita é stack ideal para tools GNOME
- Visual nativo "for free" (parece app oficial do GNOME)
- Iteração rápida (sem rebuild)
- Bibliotecas Python ricas para integração com D-Bus, dconf, systemctl, etc.
- PyGObject vem do RPM `python3-gobject` no Silverblue (sem deps externas)

### 11.3 Rust+Ratatui só compensa para CLI perfance-críticas
Activity Log core se beneficiou (parser de logs gigantes precisa ser rápido).
Para apps GUI, Python ganha em iteração. Separar core Rust + frontend Python
funcionou: Activity Log GUI consome `--output json-bundle` do core.

### 11.4 pkexec é OK para opt-in pontual; D-Bus + polkit policy para uso intenso
A cada call pkexec abre dialog. Funciona para "muda 1 setting"
(Privacy Controls system-scope). Mas para "refresh a cada 3s" é inviável —
daí o Modo admin opt-in do Network Monitor que desliga auto-refresh.

**Pattern útil**: agrupar múltiplas ops num só `pkexec bash -c '...'` para
manter 1 prompt (Hardening Checks: lynis + chmod; File Integrity: init + chmod).

### 11.5 Async subprocess é obrigatório, não opcional
UI freeze de 1-3s ao abrir tools era inaceitável. Padrão `threading.Thread` +
`GLib.idle_add` resolveu uniforme em 5 tools (Batch 1).

### 11.6 sudo + pip --user é uma armadilha
Sudo não vê `~/.local/bin/`. Solução: symlink em `/usr/local/bin/` (mutável no
Silverblue) OU `sudo -E` (preserva env). Mas no fluxo do Vigia o user nunca
deveria precisar `sudo vigia-X` — sempre via pkexec interno.

### 11.7 Master-detail evoluiu para master-detail-content (3 painéis)
Lista vertical era ok com 2-3 tools. Cards em grid eram ok com 4-5.
Master-detail funciona até ~10 tools. Com 13+, categorias se tornam
essenciais — 3 painéis (nav fina + sidebar categorizada + content) é o
formato natural.

### 11.8 Adw.Clamp é essencial para tabs não-PreferencesPage
Em janelas largas, conteúdo `Gtk.Box` puro estica edge-to-edge — visual feio.
`PreferencesPage` já clampa. Para outros containers, wrap manual em
`Adw.Clamp(maximum_size=720)`.

### 11.9 Markdown leve enriquece sem complicar a escrita
Conversor de 3 sintaxes (`**`, `*`, `` ` ``) → Pango markup foi suficiente.
Não precisa de full Markdown.

### 11.10 Descrições em pt-BR são diferencial real para SELinux/Capabilities
Booleans com nomes opacos (`httpd_can_network_connect`) ou capabilities
(`CAP_SYS_PTRACE`) ficam acessíveis com explicação humana. Vale a pena
escrever as 60+ entradas do SELinux e 41 do Capabilities Inspector.

### 11.11 Audit log do Fedora usa "enriched format"
Cada linha tem campos uppercase (`AUID`, `UID`, etc.) anexados sem espaço.
Parser precisa lidar. Também há single-quoted nested fields em USER_*
records que precisam expansão recursiva.

### 11.12 Silverblue precisa de adaptações específicas
- AIDE padrão vasculha `/usr` (read-only) → ruído inútil. Perfil custom
  focado em `/etc`, `/root`, cron.
- Lynis findings de paths read-only não são acionáveis → banners de contexto.
- `/etc/systemd/system.control/` gerado pelo systemd em runtime → exclude.
- `pip --user` + symlinks em `/usr/local/bin/` (mutável) — não tem
  `/usr/local` writable como em Workstation.

### 11.13 LGPD/escritório de advocacia muda defaults
- Reports `chmod 0600` por padrão
- Firewall zona `block` em vez de `public`
- DNS sem upstream automático
- VPN sem auto-connect
- Defaults restritivos, abrir só o necessário.

### 11.14 Wrapper de programas existentes > programas novos
VigiaOS não reinventa wheels. Wrappa programas estabelecidos
(`lynis`, `aide`, `wg-quick`, `resolvectl`, `getcap`, `firewall-cmd`,
`semanage`) com GUI moderna. O valor é UX + pt-BR + LGPD-awareness, não
implementação nova de scanning/auditoria.

### 11.15 Sub-bar `WRAPPED_PACKAGES` foi insight de UX
Tentativa inicial de pôr badges no header `pack_end` comprimia tabs
("St...", "Bo..."). Mover para sub-bar dedicada (`toolbar.add_top_bar()`)
deu transparência ao usuário (vê qual pacote upstream a tool envolve) sem
poluir header.

### 11.16 Cairo + `Gtk.DrawingArea` é viável para gráficos custom
Para gráficos dinâmicos (sparkline, line chart, stacked bar), `Cairo` via
`Gtk.DrawingArea.set_draw_func()` se mostrou rápido o suficiente para
refresh 1Hz com 8+ séries. ~220 linhas de código em `graphs.py` cobrem
3 widgets reusáveis. Alternativas (matplotlib, plotly) trariam deps
externas pesadas; libs nativas GTK4 (`Adw.AnimationTarget`?) são limitadas.

Pattern bom: `deque(maxlen=60)` por série + `push(v) → queue_draw()` no
widget. Cairo desenha em coord local; padding interno gerencia eixos +
labels. Performance: 60 pontos × 8 séries × 1Hz = ~1ms por frame.

### 11.17 `.pill` em botões action foi um erro estético
Inicialmente apliquei `.pill` em quase todo botão `.suggested-action` /
`.destructive-action` (achei que ficaria moderno). Feedback do user:
"queria retangular como o do Reports". Resultado da padronização: remoção
de pill em 27 botões. Lição: o **default GTK4** já é bom — só desviar
quando há razão clara. Manter `.pill` apenas em chips compactos com
`.flat` (atalhos tipo "Home", "Downloads").

### 11.18 Botões dentro de `Adw.PreferencesGroup` sufocam
Padrão tentador: botão de ação como última row do mesmo `PreferencesGroup`
que contém o input. **Visualmente apertado** — herda padding mínimo de
`ActionRow` e fica colado nas bordas do card. Padrão melhor: botão FORA
do card, em `Gtk.Box` própria com `margin_top(16)` e `halign=END`.
Aplicado em Hash Tools (Comparar, Criar baseline, Recarregar, Copiar) e
deve ser padrão para tools futuras.

### 11.19 `/proc` é o melhor "wrapped package" possível
Dashboard prova que para algumas tools, o "wrap" ideal não é um binário
upstream mas o **kernel direto**. `/proc/stat`, `/meminfo`, `/diskstats`,
`/net/dev` são interfaces estáveis (>20 anos), zero overhead, sem deps,
sem subprocess. Performance: ~1ms para snapshot completo do sistema.
Trade-off único: parsing manual de cada formato (mas formatos são
documentados em `man 5 proc`).

### 11.20 Refator de duplicação só funciona com retro-compat
A migração para `vigia_common` (16 tools, ~600 linhas duplicadas)
funcionou porque cada `_helpers.py` foi preservado como **fachada de
re-export**, não removido. Código existente que faz
`from .._helpers import make_clamp` continuou funcionando inalterado.

Se eu tivesse forçado migração breaking (remover `_helpers.py`,
trocar imports em todas as tabs), o blast radius seria maior:
~50 arquivos com mudanças de import, possibilidade de breakage
em algum lugar não testado. A abordagem de fachada custou ~25 linhas
por tool (16 × 25 = 400 linhas), mas isolou o blast radius ao
próprio `_helpers.py`. Lição: refatores ortogonais à API pública
têm que respeitar a fronteira existente.

### 11.21 RPM spec generation via script é robusto
17 specs Python gerados via `/tmp/generate_specs.py` com template +
dataclass. Mais resiliente que escrever manualmente (humano esquece
detalhe em 17º arquivo). Template tem ~90 linhas; cada tool adiciona
~10 linhas de config (nome, versão, deps extras, descrição).

Risk: template muda → regerar todos. Mitigação: comitar o script junto
com os specs, manter idempotente. Pré-condição: estrutura dos specs
ser uniforme (todas tools Python seguem padrão pip wheel + .desktop +
.svg + post hooks).

---

## 12. Tags de restauração

Tags criadas antes de mudanças grandes para permitir rollback fácil:

| Tag | Marco antes | Como restaurar |
|---|---|---|
| `pre-activity-log-py` | Split Activity Log core/GUI | `git checkout pre-activity-log-py -- tools/activity-log/` |
| `pre-embedded-hub` | Hub v0.4 embedded mode | `git checkout pre-embedded-hub -- tools/vigia-hub/` |
| `pre-batch-2` | Batch 2 robustez (9 fixes) | `git checkout pre-batch-2` (snapshot completo) |
| `pre-silverblue-tweaks` | Perfil AIDE Silverblue + Lynis banners | `git checkout pre-silverblue-tweaks -- tools/file-integrity/ tools/hardening-checks/` |
| `pre-layout-redesign` | Hub 3 painéis + categorias + aba Sobre | `git checkout pre-layout-redesign` |
| `pre-polish-v02` | Polish v0.2 (AIDE exclude + VPN paste) | `git checkout pre-polish-v02 -- tools/file-integrity/ tools/vpn-manager/` |
| `v0.7.0` | Activity Log core release | Tarball acessível no GitHub release |

**Commits-âncora** (sem tag formal mas referenciados no log):
- `0258a94` — Add Vigia Dashboard v0.1
- `e089e2f` — Hash Tools: botões fora dos cards
- `8198df1` — Padroniza espaçamentos em 26 arquivos
- `0b72ba8` — Antivirus v0.1.1 UX (3→4 tabs unificada)
- `2cd8862` — Remove .pill de 27 botões action

---

## 13. Troubleshooting

### `pip: command not found`
Silverblue não vem com pip. Use `rpm-ostree install python3-pip` + reboot,
OU use `python3 -m pip install --user ...`.

### `sudo vigia-X: command not found`
sudo não vê `~/.local/bin/`. Crie symlink:
```bash
sudo ln -sf "$HOME/.local/bin/vigia-X" /usr/local/bin/vigia-X
```
Ou use `sudo -E vigia-X`. **Mas idealmente nunca precise** — tools chamam
pkexec internamente.

### `ModuleNotFoundError: No module named 'vigia_X'`
Está rodando sem `pip install`. Use `PYTHONPATH=src python -m vigia_X`.
Ou faça `pip install --user -e .` no diretório do tool.

### Ícone não aparece no menu GNOME
```bash
gtk-update-icon-cache ~/.local/share/icons/hicolor 2>/dev/null
update-desktop-database ~/.local/share/applications 2>/dev/null
# Se ainda não, fazer logout/login da sessão GNOME
```

### `git pull` falha com "Cargo.lock would be overwritten"
Cargo update lockfile localmente. Descarta:
```bash
git checkout tools/activity-log/Cargo.lock
git pull
```

### pkexec dialog não aparece (timeout)
Pode ser que o polkit agent não está rodando na sessão. Em Silverblue/GNOME
deve estar sempre. Se não, `systemctl --user status xdg-desktop-portal`.

### Network Monitor: "(processo restrito)" em tudo
Esperado quando rodando como user. Ligue o switch **"Modo admin"** na UI —
abre polkit dialog e revela nomes.

### libEGL warnings na VM
Mesa tentando usar ZINK/Vulkan que não existe em VM sem GPU passthrough.
Cosmetic — pode ignorar, app funciona via software rendering.

### Hardening Checks: "Não avaliado" em todos os findings
Bug histórico (corrigido em v0.1.1): `lynis-report.dat` era `0600`
(root only), parser user-mode retornava vazio. Solução foi chmod 644 no
mesmo pkexec.

### AIDE: 10+ "modificações" em `/etc/systemd/system.control/`
Bug histórico (corrigido em v0.1.3): arquivos voláteis do systemd.
Solução foi excluir do perfil Silverblue.

### VPN dialog: não consigo colar com Ctrl+V
Bug histórico (corrigido em v0.1.1 do VPN Manager): TextView abria sem
keyboard focus. Solução: botão "Colar" no header do textarea como fallback,
`grab_focus` inicial no name_entry.

### File Integrity: `Path.is_file()` retorna False mesmo com arquivo existindo
Bug histórico (corrigido em v0.1.2): `/var/lib/aide/` era `0700`, user não
podia stat. Solução foi `chmod 755 /var/lib/aide/` no mesmo pkexec do init.

---

## Apêndice: comandos de referência rápida

```bash
# Atualizar tudo na VM
cd ~/dev/VigiaOS
git checkout tools/activity-log/Cargo.lock  # se necessário
git pull

# Activity Log core (Rust)
cd tools/activity-log
cargo build --release
sudo install -m 0755 target/release/vigia-log /usr/local/bin/vigia-log

# Tools Python (editable — só git pull já reflete)
# Mas se mudou pyproject.toml, refaz:
cd tools/<nome>
pip install --user -e .

# Symlinks sudo-friendly (todos os 16 entrypoints)
for tool in vigia-hub vigia-privacy vigia-selinux vigia-firewall vigia-netmon \
            vigia-hardening vigia-reports vigia-integrity vigia-installer \
            vigia-dns vigia-caps vigia-log-gui \
            vigia-antivirus vigia-dashboard vigia-rootkit \
            vigia-deployments; do
  sudo ln -sf "$HOME/.local/bin/$tool" /usr/local/bin/$tool
done

# Testar tudo via Hub
vigia-hub
# Ou tools individuais
vigia-log          # CLI/TUI do core Rust
vigia-log-gui      # GUI do Activity Log (Python)
vigia-privacy      # toggles
vigia-selinux      # SELinux manager
vigia-firewall     # firewalld manager
vigia-netmon       # network monitor
vigia-hardening    # Lynis wrapper
vigia-reports      # PDF LGPD
vigia-integrity    # AIDE wrapper + hashing ad-hoc (SHA/MD5)
vigia-installer    # catálogo de tools
vigia-dns          # dnscrypt-proxy manager (DoH/DNSCrypt/DNSSEC)
vigia-caps         # getcap audit
vigia-antivirus    # ClamAV wrapper
vigia-rootkit      # chkrootkit + rkhunter
vigia-deployments  # rpm-ostree manager (deployments/pinning/cleanup)
vigia-dashboard    # sistema em tempo real (CPU/RAM/disco/rede/procs)
```
