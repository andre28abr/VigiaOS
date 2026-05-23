# VigiaOS — Guia de Desenvolvimento (v2)

> **Documento vivo.** Atualizar a cada mudança significativa. Serve como
> contexto completo para retomar o desenvolvimento (humano ou IA) sem
> precisar reler histórico de PRs ou conversas anteriores.
>
> Última atualização: 2026-05-23

---

## Sumário

1. [Visão geral](#1-visão-geral)
2. [O que mudou em relação à v1](#2-o-que-mudou-em-relação-à-v1)
3. [Decisões de arquitetura](#3-decisões-de-arquitetura)
4. [Estrutura do repositório](#4-estrutura-do-repositório)
5. [Ferramentas — estado atual](#5-ferramentas--estado-atual)
6. [Padrões e convenções comuns](#6-padrões-e-convenções-comuns)
7. [Como adicionar uma ferramenta nova](#7-como-adicionar-uma-ferramenta-nova)
8. [Setup numa máquina nova (Silverblue limpa)](#8-setup-numa-máquina-nova-silverblue-limpa)
9. [Log de implementação](#9-log-de-implementação)
10. [Roadmap](#10-roadmap)
11. [Lições aprendidas](#11-lições-aprendidas)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Visão geral

**VigiaOS** é uma **suite de ferramentas** para Fedora Silverblue, focada em:

- **Segurança**: ferramentas de scan, audit, IDS, forensics
- **Privacidade**: toggles centrais de privacidade, Tor
- **LGPD/Compliance**: ferramentas de audit log e visualização
- **Network insight**: monitor de conexões em tempo real

**NÃO** é uma distribuição Linux. Usa Silverblue **vanilla** e adiciona
software por cima.

**Alvo de hardware**: aarch64 e x86_64 (Apple Silicon via UTM + PCs).

**Estado atual** (2026-05-23): **6 ferramentas funcionais** integradas via
launcher master-detail.

| Ferramenta | Versão | Stack | Status |
|---|---|---|---|
| **Vigia Hub** | v0.3.1 | Python + GTK4 + libadwaita | 🟢 Master-detail UI com markdown |
| **Activity Log** | v0.7.0 | Rust + Ratatui | 🟢 3 sources + correlations + live tail |
| **Privacy Controls** | v0.3.0 | Python + GTK4 + libadwaita | 🟢 13 toggles user+system scope |
| **SELinux Manager** | v0.2.0 | Python + GTK4 + libadwaita | 🟢 6 tabs + pt-BR + audit2allow |
| **Firewall Manager** | v0.1.0 | Python + GTK4 + libadwaita | 🟡 Status + zones CRUD |
| **Network Monitor** | v0.1.1 | Python + GTK4 + libadwaita | 🟡 Conexões + modo admin via pkexec |

---

## 2. O que mudou em relação à v1

A **v1** era uma distro completa buildada via BlueBuild — imagem container
publicada no GHCR, usuário rebasava com `rpm-ostree rebase`. Funcionava mas
trazia custos: manter pipeline de imagem (cosign, GHCR, runners ARM), brigar
com upstream Silverblue a cada release, e bug-surface próprio (theme, dconf,
GTK CSS — todos foram fontes de erros).

A **v2** (pivot em 2026-05-22) elimina a imagem e foca no que diferencia:
ferramentas próprias rodando sobre Silverblue vanilla. A v1 está preservada
em [`legacy/v1-distro`](https://github.com/andre28abr/VigiaOS/tree/legacy/v1-distro)
para consulta.

---

## 3. Decisões de arquitetura

| Decisão | Escolha | Razão |
|---|---|---|
| **Base do sistema** | Fedora Silverblue vanilla | Red Hat mantém; sem fork |
| **Distribuição** | `bootstrap.sh` + cada tool tem `pip install -e .` | Sem image build |
| **Stack GUIs** | Python + PyGObject + GTK4 + libadwaita | Stack que o GNOME usa para apps oficiais; rápido de iterar |
| **Stack CLIs perfance-críticas** | Rust + Ratatui | Activity Log precisa parsear logs rapidamente; Rust + crossterm para TUI |
| **Privilege escalation** | `pkexec` opt-in via polkit | Dialog nativo do GNOME; cancelável; sem cache (v0.x compromise) |
| **Pacotagem de comandos** | `pip install --user -e .` (editable) | Mudanças locais refletem sem reinstalar |
| **Bins acessíveis via sudo** | symlink em `/usr/local/bin/` (mutável no Silverblue) | sudo não vê `~/.local/bin/` por default |
| **Icons** | SVG 256x256, mesma paleta zinc + emerald | Identidade visual consistente |
| **Entries .desktop** | Em `~/.local/share/applications/` (escopo user) | Não polui `/usr/share/` |
| **Identidade visual** | zinc-950 bg + emerald accent | Portada do app SentinelBR do autor |

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
│   ├── vigia-activity-log.spec  # spec do Activity Log
│   ├── Makefile                 # make srpm | rpm | install-desktop
│   ├── README.md                # Instruções de COPR
│   ├── vigia-log.desktop        # GNOME entry do Activity Log
│   └── vigia-log.svg            # Icon do Activity Log
│
└── tools/                       # Uma pasta por ferramenta independente
    ├── activity-log/            # Rust — parser de logs
    ├── vigia-hub/               # Python — launcher mestre
    ├── privacy-controls/        # Python — toggles
    ├── selinux-gui/             # Python — manager SELinux
    ├── firewall-gui/            # Python — manager firewalld
    └── netmon-gui/              # Python — monitor de rede
```

Cada ferramenta em `tools/` é um **projeto independente** com seu próprio
build system (`pyproject.toml`, `Cargo.toml`). Versionam separadamente.

---

## 5. Ferramentas — estado atual

### 5.1 Vigia Hub (`tools/vigia-hub/`, v0.3.1)

**Função**: Launcher mestre. Um único ícone no menu GNOME que abre tudo.

**Stack**: Python + PyGObject + GTK4 + libadwaita + `Adw.NavigationSplitView`.

**Layout**: Master-detail (sidebar + content).
- **Sidebar**: lista de tools com ícone 40px + nome + descrição curta + status dot
- **Content**: painel detalhe completo (ícone 128px, nome, descrição longa em Markdown, features, botão Abrir)

**Componentes-chave**:
- `registry.py` — lista `TOOLS` com `ToolEntry`. Para adicionar tool nova, basta 1 entry aqui.
- `markdown.py` — conversor leve md → Pango markup (`**bold**`, `*italic*`, `` `code` ``)
- `window.py` — orquestra split view + Stack com 1 página por tool

**Como lança cada tool**:
- `needs_terminal=True` (Activity Log): wrap com `kgx` / `ptyxis` / etc. (auto-detect)
- `needs_root=True` (Activity Log): prefix `sudo`
- Caso contrário: `subprocess.Popen([cmd])`

**Detecção de "instalada"**: cada ToolEntry tem `available_fn = lambda: shutil.which("vigia-X") is not None`.

---

### 5.2 Vigia Activity Log (`tools/activity-log/`, v0.7.0)

**Função**: Parser de logs do Linux com narrativa human-readable.

**Stack**: Rust 2021 + Ratatui 0.29 + Crossterm 0.28 + Clap + Serde + Chrono.

**Sources suportadas**:
- `audit` (`/var/log/audit/audit.log`) — Linux Audit
- `journald` (via `journalctl -o json`)
- `fail2ban` (`/var/log/fail2ban.log`)

**Módulos**:
- `audit.rs` — parser de linhas audit, agrupa records por audit_id, suporta double/single-quoted nested fields + extração de `{ action }` dos AVC
- `journal.rs` — parser de JSON-lines do journalctl, mapeia `PRIORITY` syslog (0-7) para enum
- `fail2ban.rs` — parser de `YYYY-MM-DD HH:MM:SS,mmm logger [pid]: LEVEL [jail] Action IP`
- `event.rs` — enum `Event { Audit, Journal, Fail2ban }` unificada + `Severity` shared
- `narrator.rs` — dispatch para narrar em pt-BR cada tipo de evento (15+ tipos audit cobertos)
- `correlator.rs` — 4 patterns:
  - `fail2ban_burst`: N×Found mesmo IP → Ban em 2min (N≥2)
  - `oom_kill`: journal CRIT OOM, opcionalmente confirmado por audit ANOM_ABEND
  - `selinux_burst`: 3+ AVC denials mesmo comm em sliding window 60s
  - `suspicious_ssh_login`: Accepted publickey + Found anterior em fail2ban (10min)
- `live.rs` — `LiveSources` com `refresh()` para tail mode (polling 2s default)
- `tui.rs` — Ratatui App: lista navegável, filtros (`f`/`s`/`/`), live indicator, correlations panel
- `main.rs` — clap CLI com `--sources`, `--output`, `--limit`, `--min-severity`, `--follow`

**Severity classifier per-evento**:
- audit AVC permissive=0 → Suspicious; =1 → Interesting
- audit USER_AUTH/LOGIN success → Routine; failure → Suspicious
- audit USER_CMD success → Interesting (sudo escalation notável)
- journal EMERG/ALERT/CRIT → Suspicious; ERR/WARNING → Interesting; resto → Routine
- fail2ban Ban → Suspicious; Found → Interesting; Unban/Jail → Routine

**Output modes**: `tui` (default), `text`, `json` (com `source` discriminator), `correlations` (só narrativas).

**Tests**: 28 unit tests passando.

**Distribuição preparada**: RPM spec em `packaging/vigia-activity-log.spec` pronto para COPR. Tag `v0.7.0` criada no GitHub (tarball acessível).

---

### 5.3 Vigia Privacy Controls (`tools/privacy-controls/`, v0.3.0)

**Função**: 13 toggles de privacidade em uma única janela.

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Módulos**:
- `app.py` — Adw.Application
- `window.py` — Adw.ApplicationWindow + Adw.PreferencesPage (clamp automático)
- `toggles/base.py` — dataclass `Toggle` + helpers `dconf_toggle()` e `systemd_unit_toggle()`
- `toggles/dconf_toggles.py` — todos os toggles user-scope (dconf)
- `toggles/systemd_toggles.py` — toggles system-scope (Firewall, SSH, Tor)
- `toggles/bluetooth.py` — via `bluetoothctl` (precisa estar separado, não usa dconf nem systemctl)

**Toggles por categoria**:

| Categoria | Toggles |
|---|---|
| Localização | Serviços de localização |
| Telemetria | Bloquear relatórios técnicos (`report-technical-problems` invertido) |
| Histórico | Não lembrar arquivos recentes, Não lembrar uso de apps, Esconder identidade |
| Lock Screen | Bloquear tela auto, Esconder prévia notificações na lock |
| Limpeza Automática | Esvaziar lixeira auto, Limpar temp files auto |
| Rede (system) | Firewall (firewalld), Servidor SSH |
| Anonimização (system) | Serviço Tor |
| Dispositivos | Bluetooth |

**System-scope** usa `pkexec systemctl enable/disable --now <unit>` — abre polkit dialog.

---

### 5.4 Vigia SELinux Manager (`tools/selinux-gui/`, v0.2.0)

**Função**: GUI moderno para SELinux. 6 tabs.

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Módulos**:
- `backend.py` — wrappers de `getenforce`, `sestatus`, `getsebool`, `semanage`, `ausearch`, `audit2allow`, `restorecon`, `ps -eZ`
- `descriptions.py` — dict pt-BR de ~60 booleans comuns (Apache, SSH, Samba, FTP, NFS, Mail, Cron, Virt, Mozilla, etc.)
- `tabs/_helpers.py` — `make_clamp()`, `show_error()`, `show_info()` (duplicado no firewall-gui — refator futura)
- `tabs/status.py` — modo runtime + persistent (edita `/etc/selinux/config`)
- `tabs/booleans.py` — lista pesquisável com descrições, search por nome OU descrição
- `tabs/denials.py` — `pkexec ausearch -m AVC` + botão "Gerar" audit2allow
- `tabs/files.py` — `pkexec restorecon` com path input
- `tabs/network.py` — `semanage port -l` (read-only)
- `tabs/processes.py` — `ps -eZ -o label,pid,user,comm` (read-only)
- `window.py` — `Adw.ViewSwitcher` orchestrating 6 tabs

**Diferencial**: Descrições pt-BR para booleans (muito mais amigável que o output bruto do `getsebool -a`).

---

### 5.5 Vigia Firewall Manager (`tools/firewall-gui/`, v0.1.0)

**Função**: Gerenciar firewalld (zonas, services, portas).

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Módulos**:
- `backend.py` — wrappers de `firewall-cmd` (read sem privilege; write via `pkexec firewall-cmd --permanent --reload`)
- `tabs/status.py` — estado do daemon, zona padrão, zonas ativas
- `tabs/zones.py` — zone selector + CRUD de services + CRUD de portas
- `window.py` — Adw.ViewSwitcher entre 2 tabs

**Padrão write**: sempre `--permanent` + `--reload` (persiste no boot E aplica imediato). Sem necessidade de lembrar os flags.

---

### 5.6 Vigia Network Monitor (`tools/netmon-gui/`, v0.1.1)

**Função**: Conexões TCP/UDP em tempo real.

**Stack**: Python + PyGObject + GTK4 + libadwaita.

**Módulos**:
- `backend.py` — parser de `ss -tunap` (output em texto, parsed via regex)
- `tabs/connections.py` — todas conexões + auto-refresh + search + Modo admin opt-in
- `tabs/listening.py` — subclass de ConnectionsTab, override `_fetch()` para `list_listening()`
- `window.py` — 2 tabs

**Modo admin opt-in**: Switch na UI que, quando ON, faz backend chamar `pkexec ss -tunap` (revela nomes de processos do sistema). Auto-refresh fica desabilitado nesse modo (não spammar polkit).

---

## 6. Padrões e convenções comuns

### 6.1 Stack consistente
- **GUIs**: Python 3.11+, PyGObject, GTK 4, libadwaita.
- **CLI perfance-críticas**: Rust 2021, Ratatui, Crossterm.
- **Sem deps externas pip** se possível (PyGObject vem do RPM `python3-gobject`).

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
    ├── __init__.py            # __version__, __app_id__
    ├── __main__.py            # entrypoint
    ├── app.py                 # Adw.Application
    ├── window.py              # janela principal
    ├── backend.py             # subprocess wrappers
    └── tabs/                  # se a janela tem múltiplas tabs
        ├── __init__.py        # registra todas as tabs
        ├── _helpers.py        # show_error, make_clamp (duplicado entre tools — refator pendente)
        └── <tab>.py
```

### 6.3 Ícones SVG

Formato: 256x256 viewBox.

Estrutura padrão:
- Fundo: rounded square (rx=48), gradient zinc-900 → zinc-950
- Glow radial sutil emerald (opacidade 0.18-0.20)
- Motivo central da ferramenta (eye, padlock, shield, brick wall, network graph, etc.)
- Wordmark inferior: "VIGIA·<TOOL>" em JetBrains Mono, com `·` em emerald

Paleta:
- `#09090b` — zinc-950 (bg principal)
- `#18181b` — zinc-900 (bg cards)
- `#fafafa` — zinc-50 (texto principal)
- `#34d399` — emerald-400 (accent)
- `#fbbf24` — amber-400 (warning)
- `#f87171` — red-400 (error)

### 6.4 Privilege escalation via pkexec

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

Usado em: SELinux, Firewall, Privacy Controls (system-scope), Network Monitor (modo admin).

### 6.5 Adw.Clamp para limitar largura

Tabs custom (Gtk.Box) precisam Clamp manual. Tabs `Adw.PreferencesPage` já clampam por padrão. Padrão:

```python
inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_*=12)
self.append(make_clamp(inner))  # max 720px (ou 900 para network monitor)
```

### 6.6 Instalação .desktop + icon

Cada ferramenta segue:
```bash
mkdir -p ~/.local/share/applications ~/.local/share/icons/hicolor/scalable/apps
cp data/<app-id>.desktop ~/.local/share/applications/
cp data/<app-id>.svg ~/.local/share/icons/hicolor/scalable/apps/
gtk-update-icon-cache ~/.local/share/icons/hicolor 2>/dev/null || true
update-desktop-database ~/.local/share/applications 2>/dev/null || true
```

### 6.7 Sudo + pip --user

Problema: `pip install --user` instala em `~/.local/bin/`, sudo não vê.
Solução: symlink em `/usr/local/bin/` (que aponta para `/var/usrlocal/bin/`, mutável no Silverblue):
```bash
for tool in vigia-hub vigia-privacy vigia-selinux vigia-firewall vigia-netmon; do
  sudo ln -sf "$HOME/.local/bin/$tool" /usr/local/bin/$tool
done
```

Ou usar `sudo -E vigia-X` (preserva env).

---

## 7. Como adicionar uma ferramenta nova

1. **Cria o diretório** `tools/<nome>/`
2. **Copia estrutura** de uma ferramenta existente (e.g., selinux-gui)
3. **Adapta** pyproject.toml (nome, version, entry_point), __init__.py (`__app_id__`)
4. **Implementa** backend.py + window.py + tabs/
5. **Desenha ícone** SVG 256x256 seguindo a paleta (rounded square zinc + emerald + motivo + wordmark)
6. **Cria** data/<app-id>.desktop
7. **Adiciona ao registry do Hub** em `tools/vigia-hub/src/vigia_hub/registry.py`:
   ```python
   ToolEntry(
       id="meu-tool",
       name="Meu Tool",
       description="...",
       long_description="...",  # Markdown
       features=[...],
       icon_path=_TOOLS_DIR / "meu-tool" / "data" / "br.com.vigia.MeuTool.svg",
       exec_cmd=["vigia-meu-tool"],
       needs_terminal=False,
       available_fn=lambda: shutil.which("vigia-meu-tool") is not None,
   ),
   ```
8. **Atualiza** README.md do root com a nova entrada
9. **Adiciona seção** neste DEVELOPMENT.md (subseção 5.X)

---

## 8. Setup numa máquina nova (Silverblue limpa)

### 8.1 Layer dependencies via rpm-ostree

```bash
sudo rpm-ostree install \
    git rust cargo \
    python3-gobject python3-pip \
    libadwaita gtk4
systemctl reboot
```

### 8.2 Clone + instalar todas as ferramentas

```bash
mkdir -p ~/dev && cd ~/dev
git clone https://github.com/andre28abr/VigiaOS.git
cd VigiaOS

# Activity Log (Rust)
cd tools/activity-log
cargo build --release
sudo install -m 0755 target/release/vigia-log /usr/local/bin/vigia-log

# Tools Python — editable install user-scope
cd ../vigia-hub          && pip install --user -e .
cd ../privacy-controls   && pip install --user -e .
cd ../selinux-gui        && pip install --user -e .
cd ../firewall-gui       && pip install --user -e .
cd ../netmon-gui         && pip install --user -e .

# Symlink em /usr/local/bin para acesso via sudo
for tool in vigia-hub vigia-privacy vigia-selinux vigia-firewall vigia-netmon; do
  sudo ln -sf "$HOME/.local/bin/$tool" /usr/local/bin/$tool
done

# Entry no menu GNOME (só o Hub, ou todos individuais)
mkdir -p ~/.local/share/applications ~/.local/share/icons/hicolor/scalable/apps
cp tools/vigia-hub/data/br.com.vigia.Hub.* ~/.local/share/applications/ \
   ~/.local/share/icons/hicolor/scalable/apps/  # adaptar paths
gtk-update-icon-cache ~/.local/share/icons/hicolor 2>/dev/null || true
update-desktop-database ~/.local/share/applications 2>/dev/null || true
```

### 8.3 Bootstrap.sh (opcional, instala suite completa de ferramentas de segurança)

```bash
curl -fsSL https://raw.githubusercontent.com/andre28abr/VigiaOS/main/bootstrap.sh | bash
systemctl reboot
```

Instala: nmap, tcpdump, wireshark, lynis, aide, chkrootkit, fail2ban, yara, age, etc. + Flatpaks (Tor Browser, KeePassXC, Signal).

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
- v0.8 (packaging): RPM spec + Makefile + LICENSE + Tag v0.7.0
- v0.7.1: 10+ narrators audit + Nerd Fonts column width

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
- v0.2: 6 tabs (+ Denials/audit2allow, Files/restorecon, Network, Processes) + descrições pt-BR + persistent mode + Adw.Clamp

### 2026-05-22 — Firewall Manager v0.1
- Status + Zones CRUD via `pkexec firewall-cmd --permanent --reload`

### 2026-05-22 — Network Monitor v0.1 a v0.1.1
- v0.1: parser `ss -tunap` + 2 tabs (Conexões, Listening) + auto-refresh
- v0.1.1: Modo admin opt-in via pkexec

---

## 10. Roadmap

### Próximas iterações por ferramenta

**Vigia Hub v0.4+**:
- Status indicators mais ricos (versão instalada de cada tool)
- Settings global (tema, fonte, autostart de algumas tools)
- Notificações desktop quando tools terminam tarefas longas

**Activity Log v0.8+**:
- Empacotamento RPM via COPR (spec já existe, falta criar conta COPR e push)
- Modo `--watch <pattern>`: alerta quando padrão específico aparece
- Integração com inotify para refresh sub-segundo

**Privacy Controls v0.4+**:
- D-Bus helper + polkit policy com `auth_admin_keep` (cache 5min)
- Toggles novos: DNS over TLS, screen lock timeout customizado, camera/mic per-app
- Profiles: "Modo Paranóia" (todos OFF), "Modo Confiança" (padrão), "Modo Custom"

**SELinux Manager v0.3+**:
- Adicionar/remover ports (atualmente só read-only)
- File contexts customizados (`semanage fcontext`)
- Compilar+instalar policy do audit2allow com 1 botão
- Login mappings, user contexts (tabs novas)

**Firewall Manager v0.2+**:
- Rich rules editor (rate-limit, log action, family=ipv6)
- ICMP block / masquerade / port-forwarding
- Profile presets ("Modo trabalho", "Modo público", "Modo paranóia")
- Service editor (criar service custom além dos pré-definidos)

**Network Monitor v0.2+**:
- DNS reverse lookup opcional (async em background)
- Bandwidth por processo via `nethogs`
- Históricos curtos (5min back), gráficos de throughput
- Filtros pré-definidos: "Só HTTPS", "Só local", "Suspeitos"
- Integração com Firewall ("bloquear esse IP") e Activity Log

### Ferramentas novas planejadas

**Vigia Hardening Checks** (v1.0 alvo):
- Wrapper de Lynis (`lynis audit system`)
- UI com findings categorizados
- Exporta relatório para LGPD compliance
- Stack: Python + GTK4

**Vigia Reports** (v1.0 alvo):
- Gera PDF/HTML usando Activity Log como engine
- "Atividade dos últimos 7 dias", "Eventos suspeitos", "Acessos administrativos"
- Templates por tipo de compliance (LGPD, ISO 27001)
- Stack: Python + Jinja2 + WeasyPrint

**Vigia File Integrity** (v1.0 alvo):
- AIDE wrapper com UI
- Monitor de arquivos sensíveis
- Alerta quando arquivos críticos mudam

**Vigia Tool Installer** (v1.x):
- Catálogo visual de ferramentas com descrições ricas
- One-click install via `rpm-ostree install`
- Tipo "GNOME Software" mas com curadoria de security tools

**Vigia VPN Manager** (v1.x):
- Perfis WireGuard / OpenVPN
- Conexão one-click

**Vigia DNS Manager** (v1.x):
- DNS over TLS / DNS over HTTPS
- Custom resolvers, blocklists (Pi-hole-like local)

**Vigia Capabilities Inspector** (v2.x):
- Visualizador de capabilities (`getcap`)
- Audit fino além do SELinux

### Empacotamento e distribuição (meta-trabalho)

- **COPR project `andre28abr/vigia`**: criar conta + projeto + webhook SCM
- Spec files RPM para TODAS as ferramentas (já tem do Activity Log; precisa para as 5 Python tools)
- Bootstrap completo: depois de COPR ativo, usuário roda 1 comando para ter toda a suite

### Refatorações técnicas pendentes

- **`_helpers.py` duplicado** entre selinux-gui/firewall-gui/netmon-gui → extrair para um `vigia_common` shared package
- **Markdown converter** está só no Hub → mover para `vigia_common` também
- **Pattern de pkexec + tratamento de "Request dismissed"** se repete em vários backends — abstrair
- **D-Bus service compartilhado** com polkit policy `auth_admin_keep` para evitar polkit dialog repetitivo

---

## 11. Lições aprendidas

### 11.1 Pivot v1 → v2 valeu a pena
Custo de manter image build era alto demais para retorno. Ferramentas individuais são muito mais sustentáveis. Cada uma resolve um problema concreto.

### 11.2 Python + GTK4 + libadwaita é stack ideal para tools GNOME
- Visual nativo "for free" (parece app oficial do GNOME)
- Iteração rápida (sem rebuild)
- Bibliotecas Python ricas para integração com D-Bus, dconf, systemctl, etc.
- PyGObject vem do RPM `python3-gobject` no Silverblue (sem deps externas)

### 11.3 Rust+Ratatui só compensa para CLI perfance-críticas
Activity Log se beneficiou (parser de logs gigantes precisa ser rápido). Para apps GUI, Python ganha em iteração.

### 11.4 pkexec é OK para opt-in pontual; D-Bus + polkit policy para uso intenso
A cada call pkexec abre dialog. Funciona para "muda 1 setting" (Privacy Controls system-scope). Mas para "refresh a cada 3s" é inviável — daí o Modo admin opt-in do Network Monitor que desliga auto-refresh.

### 11.5 sudo + pip --user é uma armadilha
Sudo não vê `~/.local/bin/`. Solução: symlink em `/usr/local/bin/` (mutável no Silverblue) OU `sudo -E` (preserva env).

### 11.6 Master-detail (Adw.NavigationSplitView) é o layout natural para hubs
Lista vertical era ok com 2-3 tools. Cards em grid eram ok com 4-5. Master-detail funciona para qualquer quantidade e tem espaço para informação rica no detalhe.

### 11.7 Adw.Clamp é essencial para tabs não-PreferencesPage
Em janelas largas, conteúdo `Gtk.Box` puro estica edge-to-edge — visual feio. PreferencesPage já clampa. Para outros containers, wrap manual em `Adw.Clamp(maximum_size=720)`.

### 11.8 Markdown leve enriquece sem complicar a escrita
Conversor de 3 sintaxes (`**`, `*`, `` ` ``) → Pango markup foi suficiente. Não precisa de full Markdown.

### 11.9 Descrições em pt-BR são diferencial real para SELinux
Booleans com nomes opacos (`httpd_can_network_connect`) ficam acessíveis com explicação humana. Vale a pena escrever as 60+ entradas no `descriptions.py`.

### 11.10 Audit log do Fedora usa "enriched format"
Cada linha tem campos uppercase (`AUID`, `UID`, etc.) anexados sem espaço de separação. Parser precisa lidar com isso. Também há single-quoted nested fields em USER_* records que precisam de expansão recursiva.

---

## 12. Troubleshooting

### `pip: command not found`
Silverblue não vem com pip. Use `rpm-ostree install python3-pip` + reboot, OU use `python3 -m pip install --user ...`.

### `sudo vigia-X: command not found`
sudo não vê `~/.local/bin/`. Crie symlink:
```bash
sudo ln -sf "$HOME/.local/bin/vigia-X" /usr/local/bin/vigia-X
```
Ou use `sudo -E vigia-X`.

### `ModuleNotFoundError: No module named 'vigia_X'`
Está rodando sem `pip install`. Use `PYTHONPATH=src python -m vigia_X`. Ou faça `pip install --user -e .` no diretório do tool.

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
Pode ser que o polkit agent não está rodando na sessão. Em Silverblue/GNOME deve estar sempre. Se não, `systemctl --user status xdg-desktop-portal`.

### Network Monitor: "(processo restrito)" em tudo
Esperado quando rodando como user. Ligue o switch **"Modo admin"** na UI — abre polkit dialog e revela nomes.

### libEGL warnings na VM
Mesa tentando usar ZINK/Vulkan que não existe em VM sem GPU passthrough. Cosmetic — pode ignorar, app funciona via software rendering.

---

## Apêndice: comandos de referência rápida

```bash
# Atualizar tudo na VM
cd ~/dev/VigiaOS
git checkout tools/activity-log/Cargo.lock  # se necessário
git pull

# Activity Log (Rust)
cd tools/activity-log
cargo build --release
sudo install -m 0755 target/release/vigia-log /usr/local/bin/vigia-log

# Tools Python (editable — só git pull já reflete)
# Mas se mudou pyproject.toml, refaz:
cd tools/<nome>
pip install --user -e .

# Symlinks sudo-friendly
for tool in vigia-hub vigia-privacy vigia-selinux vigia-firewall vigia-netmon; do
  sudo ln -sf "$HOME/.local/bin/$tool" /usr/local/bin/$tool
done

# Testar
vigia-hub        # launcher
vigia-log        # CLI/TUI logs
vigia-privacy    # toggles
vigia-selinux    # SELinux manager
vigia-firewall   # firewalld manager
vigia-netmon     # network monitor
```
