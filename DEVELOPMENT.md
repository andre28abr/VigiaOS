# VigiaOS — Guia de Desenvolvimento (v2)

> **Documento vivo.** Atualizar a cada mudança significativa. Serve como
> contexto completo para retomar o desenvolvimento (humano ou IA) sem
> precisar reler histórico de PRs ou conversas anteriores.
>
> Última atualização: 2026-05-25 (revisão 2: +4 tools novas)

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
- **Privacidade**: toggles centrais, Tor, DNS over TLS
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

**Estado atual** (2026-05-25): **17 ferramentas funcionais** integradas
via Hub com layout master-detail-content (3 painéis) + categorias +
modo embedded.

| # | Ferramenta | Versão | Stack | Status |
|---|---|---|---|---|
| 1 | **Vigia Hub** | v0.5.0 | Python + GTK4 + libadwaita | 🟢 3 painéis (nav + categorias + content), embedded |
| 2 | **Activity Log (core)** | v0.7.1 (Rust) | Rust + Ratatui + Crossterm | 🟢 3 sources + correlations + JsonBundle |
| 3 | **Activity Log (GUI)** | v0.1.0 | Python + GTK4 | 🟢 Frontend do core Rust via JSON |
| 4 | **Privacy Controls** | v0.3.0 | Python + GTK4 | 🟢 13 toggles user+system scope |
| 5 | **SELinux Manager** | v0.2.0 | Python + GTK4 | 🟢 6 tabs + pt-BR + audit2allow + lazy tabs |
| 6 | **Firewall Manager** | v0.1.0 | Python + GTK4 | 🟡 Status + zones CRUD |
| 7 | **Network Monitor** | v0.1.0 | Python + GTK4 | 🟡 Conexões + modo admin + auto-refresh smart |
| 8 | **Hardening Checks** | v0.1.2 | Python + GTK4 | 🟢 Lynis wrapper + perfil Silverblue |
| 9 | **Reports** | v0.1.1 | Python + GTK4 + Jinja2 + WeasyPrint | 🟢 PDF/HTML LGPD via Activity Log JSON |
| 10 | **File Integrity** | v0.1.3 | Python + GTK4 | 🟢 AIDE wrapper + perfil Silverblue customizado |
| 11 | **Tool Installer** | v0.1.0 | Python + GTK4 | 🟢 Catálogo curado via `rpm-ostree install` |
| 12 | **VPN Manager** | v0.1.1 | Python + GTK4 | 🟢 WireGuard wrapper + paste fallback |
| 13 | **DNS Manager** | v0.1.0 | Python + GTK4 | 🟢 systemd-resolved + 9 providers DoT |
| 14 | **Capabilities Inspector** | v0.1.0 | Python + GTK4 | 🟢 getcap audit + catálogo pt-BR de 41 caps |
| 15 | **Antivirus** | v0.1.0 | Python + GTK4 | 🟢 ClamAV wrapper — substitui clamtk |
| 16 | **Network Scanner** | v0.1.0 | Python + GTK4 | 🟢 nmap GUI com 6 perfis pré-definidos |
| 17 | **Firmware Analyzer** | v0.1.0 | Python + GTK4 | 🟢 binwalk: signatures + extract + entropia |
| 18 | **Hash Tools** | v0.1.0 | Python + GTK4 | 🟢 SHA-256/512 + baseline+diff de diretório |

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
NetMon). Expandiu para **17 ferramentas** em 4 ciclos:

| Ciclo | Adições | Foco |
|---|---|---|
| **Inicial** | Hub + 5 tools | Master-detail layout, fundação |
| **Compliance/audit** | Hardening Checks, Reports, File Integrity, Tool Installer, Activity Log GUI | LGPD + audit estendido |
| **Network/integrity** | VPN, DNS, Capabilities | Camada de rede privada + audit fino |
| **Security toolkit** | Antivirus, Network Scanner, Firmware Analyzer, Hash Tools | Análise prática (scan/RE/integrity) |

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
    ├── tool-installer/          # Python — catálogo via rpm-ostree
    ├── vpn-manager/             # Python — wrapper WireGuard
    ├── dns-manager/             # Python — wrapper systemd-resolved
    ├── capabilities-inspector/  # Python — getcap audit
    ├── antivirus/               # Python — wrapper ClamAV
    ├── network-scanner/         # Python — GUI nmap
    ├── firmware-analyzer/       # Python — wrapper binwalk
    └── hash-tools/              # Python — hash + baseline diff
```

Cada ferramenta em `tools/` é um **projeto independente** com seu próprio
build system (`pyproject.toml`, `Cargo.toml`). Versionam separadamente.

---

## 5. Catálogo de ferramentas — estado atual

### 5.1 Vigia Hub (`tools/vigia-hub/`, v0.5.0)

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
│      │  • VPN        │                                   │
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

**Categorias** (`registry.py`):
- `monitoramento` — Activity Log, NetMon
- `privacidade` — Privacy Controls, DNS, VPN
- `defesa` — Firewall, SELinux, Hardening Checks, File Integrity, Capabilities
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
usuário sobre o que está sendo envolvido (ex: `lynis`, `wireguard-tools`,
`systemd-resolved`).

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

### 5.4 Vigia Privacy Controls (`tools/privacy-controls/`, v0.3.0)

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
| Anonimização (system) | Serviço Tor |
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

### 5.7 Vigia Network Monitor (`tools/netmon-gui/`, v0.1.0)

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

### 5.8 Vigia Hardening Checks (`tools/hardening-checks/`, v0.1.2)

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

### 5.10 Vigia File Integrity (`tools/file-integrity/`, v0.1.3)

**Função**: Wrapper de AIDE (Advanced Intrusion Detection Environment).

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Tabs**: Status (+ controles do perfil Silverblue) + Init/Update + Check +
Histórico + Sobre.

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

**Wrapper de**: `aide`.

---

### 5.11 Vigia Tool Installer (`tools/tool-installer/`, v0.1.0)

**Função**: Catálogo curado de ferramentas de segurança instaláveis via
`rpm-ostree install` ou `flatpak install`.

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Categorias** (~30 ferramentas catalogadas):
- Network — nmap, tcpdump, wireshark, ncat, mtr
- Forensics — sleuthkit, foremost, scalpel
- Malware — yara, chkrootkit, rkhunter
- Crypto — age, gpg, keepassxc
- Logs — fail2ban (já wrappado em parte pelo Activity Log)
- Flatpaks — Tor Browser, Signal, KeePassXC GUI

**Padrão**: chama `pkexec rpm-ostree install <pkg>` async + status visual.
Reboot recomendado após install.

**Lazy refresh** (Batch 1, P1): catálogo carrega em thread, UI mostra
skeleton até concluir.

**Posicionamento no Hub**: NÃO aparece na sidebar de tools — fica como
ícone fixo na nav lateral fina (visual de "settings"), não compete com
ferramentas de uso diário.

**Wrapper de**: `rpm-ostree`, `flatpak`.

---

### 5.12 Vigia VPN Manager (`tools/vpn-manager/`, v0.1.1)

**Função**: Wrapper GUI de WireGuard (`wg-quick`).

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Tabs**: Status + Perfis + Sobre.

**Operações**:
- Listar configs em `/etc/wireguard/*.conf` (via `pkexec ls`)
- Conectar (`pkexec wg-quick up <name>`)
- Desconectar (`pkexec wg-quick down <name>`)
- Importar perfil (cola conteúdo de `.conf` → salva em
  `/etc/wireguard/<name>.conf` com heredoc UUID-delimited)

**Dialog de import — paste fallback** (polish v0.2, `e5011e4`):
- Original: `TextView` não recebia Ctrl+V porque dialog abria sem keyboard
  focus.
- Fix: `set_editable(True)`, `set_can_focus(True)`, `set_accepts_tab(False)`,
  botão "Colar" no header do textarea com fallback via
  `Gdk.Display.get_clipboard().read_text_async()`, `grab_focus` inicial no
  `name_entry` via `GLib.idle_add`.

**Heredoc UUID-delimited**: para escrever config sem injeção shell,
`bash -c "cat > /etc/wireguard/$NAME.conf << '$UUID'\n$CONTENT\n$UUID"`. UUID
random a cada call evita colisão se conteúdo tiver "EOF" literal.

**SVG**: tunnel concept (2 endpoints + curva + lock no meio).

**Wrapper de**: `wireguard-tools` (binários `wg`, `wg-quick`).

---

### 5.13 Vigia DNS Manager (`tools/dns-manager/`, v0.1.0)

**Função**: Wrapper de `systemd-resolved` + `resolvectl`. Configura DNS
over TLS (DoT) com providers curados.

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Tabs**: Status (DNS atual, DoT enabled?) + Provedores (catálogo) + Sobre.

**Catálogo (9 providers)**:
| Provider | Variantes |
|---|---|
| Cloudflare | Standard, Malware-blocking, Family |
| Quad9 | Standard |
| AdGuard | Standard, Family |
| Mullvad | Standard, Adblock |
| Google | Standard |

**Padrão**: edita `/etc/systemd/resolved.conf` (com backup automático
`.vigia-backup` antes de cada write) + `pkexec systemctl restart
systemd-resolved`.

**Particularidades de naming**: tem `resolvers.py` (catálogo de providers)
E `tabs/resolvers.py` (tab UI). Para evitar colisão de import, criou-se
`_resolvers_module.py` como wrapper de import.

**SVG**: globe with meridians + lock no centro.

**Wrapper de**: `systemd-resolved` (binário `resolvectl`).

---

### 5.14 Vigia Capabilities Inspector (`tools/capabilities-inspector/`, v0.1.0)

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

### 5.15 Vigia Antivirus (`tools/antivirus/`, v0.1.0)

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

### 5.16 Vigia Network Scanner (`tools/network-scanner/`, v0.1.0)

**Função**: GUI moderna para nmap — discovery e port scan com perfis
pré-definidos.

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Tabs**: Scan (target + perfil + run) + Hosts (histórico) + Perfis
(catálogo) + Sobre.

**6 perfis** em `profiles.py` (dataclass `ScanProfile`):
| Perfil | Args | Root? | Velocidade | Intrusividade |
|---|---|---|---|---|
| Discovery (ping scan) | `-sn` | não | rápido | baixo |
| Quick (top 100) | `-F` | não | rápido | baixo |
| Standard (top 1000 + version) | `-sV` | não | médio | médio |
| Stealth (SYN scan) | `-sS -sV` | sim | médio | médio |
| Aggressive (-A) | `-A` | sim | lento | alto |
| Full (todas) | `-p- -sV` | não | lento | alto |

**Parse XML do nmap**: `nmap -oX -` → `ElementTree.fromstring()` → estrutura
`Host(address, hostname, status, ports)` com `Port(port, protocol, state,
service, product, version)`.

**Validação de target**: regex `^[a-zA-Z0-9.\-_:/, ]+$` rejeita chars de
shell injection. Aceita IPv4, IPv6, hostname, CIDR.

**Uso ético**: banner no header da aba Scan + seção dedicada na aba Sobre
explicando art. 154-A do CP (Lei Carolina Dieckmann).

**Histórico**: em `~/.local/share/vigia-netscan/scan-<timestamp>.json`
com `chmod 0600` (inclui hosts + portas + versões detectadas).

**SVG**: radar (círculos concêntricos) com nós descobertos + cone de varredura.

**Wrapper de**: `nmap`.

---

### 5.17 Vigia Firmware Analyzer (`tools/firmware-analyzer/`, v0.1.0)

**Função**: GUI para binwalk — análise de firmware de roteadores, IoT,
cameras IP e binários genéricos.

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Tabs**: Analisar (signatures) + Extrair + Entropia + Sobre.

**Operações** (sem pkexec — binwalk roda em arquivos que o user lê):
- `analyze_blocking(path)` → `binwalk <path>` → parse output texto →
  `list[Signature(offset, offset_hex, description)]`
- `extract_blocking(path, outdir)` → `binwalk -e --directory <out> <path>`
  → conta arquivos em `_<basename>.extracted/`
- `entropy_blocking(path)` → `binwalk -E --nplot` → parse edges →
  `list[EntropyPoint(offset, entropy)]`

**Entropia (qualitativa)** — labels visuais por faixa:
- <0.3: "padrão repetitivo" (verde)
- 0.3-0.6: "dados estruturados" (verde)
- 0.6-0.85: "dados densos" (dim)
- >0.95: "compactado/encryptado" (warning)

**Casos de uso documentados na aba Sobre**: auditar firmware antes de
instalar em câmeras IP / roteadores num escritório (LGPD context).

**Limitação v0.1**: gráfico visual de entropia (Cairo) fica para v0.2.
v0.1 mostra apenas edges com labels qualitativos.

**SVG**: chip em camadas (firmware → bytes → arquivos extraídos → report).

**Wrapper de**: `binwalk`.

---

### 5.18 Vigia Hash Tools (`tools/hash-tools/`, v0.1.0)

**Função**: Cálculo e verificação de hashes criptográficos, + baseline
diff de diretório.

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Tabs**: Hash (single file) + Verificar (compare expected vs computed) +
Baseline (snapshot + diff) + Sobre.

**Algoritmos** (`hashlib` stdlib, sem subprocess):
- SHA-256 (default)
- SHA-512
- SHA-1 (depreciado, só compat legacy)
- MD5 (quebrado, só compat legacy)

**Hash streaming**: lê em chunks de 1 MB (`f.read(1 << 20)`) — funciona
em arquivos grandes sem carregar tudo na memória.

**Baseline JSON format**:
```json
{
  "directory": "/etc",
  "algorithm": "sha256",
  "created_at": "2026-05-25T14:30:00",
  "file_count": 1247,
  "hashes": {
    "passwd": "abc123...",
    "hostname": "def456...",
    ...
  }
}
```

**Diff visual**: 3 categorias com badges colorides:
- MOD (warning/amarelo) — modificado
- ADD (success/verde) — adicionado
- REM (error/vermelho) — removido

Limit de 30 paths visíveis por categoria + "... +N more" para não estourar.

**Complementar a `vigia-integrity` (AIDE)**: AIDE é mais robusto (mtime,
size, perms, inode, link target, attrs), `vigia-hash` é mais simples
(só conteúdo). Use AIDE para `/etc/` + system files; use Hash Tools para
projetos/diretórios específicos.

**Copy to clipboard**: 1 clique no botão "Copiar" → hash no clipboard
via `Gdk.Display.get_clipboard().set(text)`.

**Limitação v0.1**: `hashdeep` paralelo (multi-thread) chega em v0.2.
v0.1 usa `hashlib` single-threaded — pode ser lento em diretórios com
100k+ arquivos.

**Baselines**: `~/.local/share/vigia-hash/baseline-<dirname>-<ts>.json`
com `chmod 0600` (LGPD).

**SVG**: documento → função hash (caixa com `#`) → digest (blocos hex).

**Wrapper de**: `coreutils` (sha256sum/512/1, md5sum) + `hashdeep`.

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
for tool in vigia-hub vigia-privacy vigia-selinux vigia-firewall vigia-netmon \
            vigia-hardening vigia-reports vigia-integrity vigia-installer \
            vigia-vpn vigia-dns vigia-capabilities vigia-activity; do
  sudo ln -sf "$HOME/.local/bin/$tool" /usr/local/bin/$tool
done
```

---

## 7. Como adicionar uma ferramenta nova

1. **Cria o diretório** `tools/<nome>/`
2. **Copia estrutura** de uma ferramenta existente (e.g., `vpn-manager` se
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
    wireguard-tools \
    systemd-resolved \
    clamav clamav-update \
    nmap binwalk hashdeep
systemctl reboot
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
         vpn-manager dns-manager capabilities-inspector activity-log-gui \
         antivirus network-scanner firmware-analyzer hash-tools; do
  (cd ../$d && pip install --user -e .)
done

# Symlink em /usr/local/bin para acesso via sudo
for tool in vigia-hub vigia-privacy vigia-selinux vigia-firewall vigia-netmon \
            vigia-hardening vigia-reports vigia-integrity vigia-installer \
            vigia-vpn vigia-dns vigia-capabilities vigia-log-gui \
            vigia-antivirus vigia-netscan vigia-firmware vigia-hash; do
  sudo ln -sf "$HOME/.local/bin/$tool" /usr/local/bin/$tool
done

# Entry no menu GNOME (só o Hub recomendado — ele lança as outras)
mkdir -p ~/.local/share/applications ~/.local/share/icons/hicolor/scalable/apps
cp tools/vigia-hub/data/br.com.vigia.Hub.desktop ~/.local/share/applications/
cp tools/vigia-hub/data/br.com.vigia.Hub.svg ~/.local/share/icons/hicolor/scalable/apps/
gtk-update-icon-cache ~/.local/share/icons/hicolor 2>/dev/null || true
update-desktop-database ~/.local/share/applications 2>/dev/null || true
```

### 8.3 Bootstrap.sh (one-shot)

```bash
curl -fsSL https://raw.githubusercontent.com/andre28abr/VigiaOS/main/bootstrap.sh | bash
systemctl reboot
```

Instala layered deps + clona repo + pip installs + symlinks + .desktop +
sugere Flatpaks (Tor Browser, KeePassXC, Signal) via Tool Installer.

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

**VPN Manager v0.2+**:
- Auto-connect em redes específicas (SSID-based)
- Stats: bytes in/out por sessão
- Suporte OpenVPN (atualmente só WireGuard)

**DNS Manager v0.2+**:
- Blocklists locais (Pi-hole-like)
- Stats: queries blocked/answered
- DNSSEC validation toggle

**Capabilities Inspector v0.2+**:
- Modificação de capabilities (`setcap`) com confirmação forte
- Comparativo "expected vs actual" baseado em policy
- Export findings para Activity Log

### 10.2 Ferramentas novas planejadas (post-v0.1)

**Antivirus / Network Scanner / Firmware Analyzer / Hash Tools** — IMPLEMENTADAS
no ciclo 2026-05-25 (security toolkit). Roadmap delas em §10.1 acima.

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
  9 tools (~600 linhas duplicadas) + `markdown.py` do Hub
- **D-Bus service compartilhado** com polkit policy `auth_admin_keep` para
  evitar polkit dialog repetitivo em ops batch
- **Padrão de pkexec + tratamento de "Request dismissed"** abstrair em
  helper único
- **Testes**: adicionar `pytest` para backends Python (atualmente só
  Activity Log Rust tem tests)

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

# Symlinks sudo-friendly (todos os 17 entrypoints)
for tool in vigia-hub vigia-privacy vigia-selinux vigia-firewall vigia-netmon \
            vigia-hardening vigia-reports vigia-integrity vigia-installer \
            vigia-vpn vigia-dns vigia-capabilities vigia-log-gui \
            vigia-antivirus vigia-netscan vigia-firmware vigia-hash; do
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
vigia-integrity    # AIDE wrapper
vigia-installer    # catálogo de tools
vigia-vpn          # WireGuard manager
vigia-dns          # systemd-resolved manager
vigia-capabilities # getcap audit
vigia-antivirus    # ClamAV wrapper
vigia-netscan      # nmap GUI
vigia-firmware     # binwalk wrapper
vigia-hash         # hash + baseline
```
