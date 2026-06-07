# Visão geral do VigiaOS (técnico)

## O que é

VigiaOS é **um app desktop** (GTK4 + libadwaita, `application_id`
`br.com.vigia.OS`) com um **rail de seções** — **Início** (monitor do
sistema), **Hub** (14 ferramentas de segurança/privacidade), **Red**
(pentest, esqueleto) e **Blue** (SOC) — focado em segurança, privacidade
e conformidade com LGPD para Fedora Workstation. Lançado por `vigia-os`
(aliases `vigia-hub`/`vigia-blue`/`vigia-red` abrem o app já na seção).

Não é uma distribuição Linux — é um **toolkit** que roda sobre o Fedora
Workstation vanilla. As ferramentas das seções Hub/Red/Blue compartilham
o mesmo master-detail; Red/Blue entram via adaptador `Module → ToolEntry`.

## Stack tecnológica

| Camada | Tecnologia |
|---|---|
| GUI | Python 3.11+ · PyGObject · GTK4 · libadwaita 1 |
| Lib interna | `vigia-common` (helpers compartilhados) |
| Activity Log core | Rust + Ratatui (TUI) |
| Reports | Jinja2 + WeasyPrint (PDF) |
| Tray icon | AyatanaAppIndicator3 (subprocess GTK3) |
| Autenticação | pkexec + Polkit (via `Gio.Subprocess` async) |
| State local | JSON em `~/.config/vigia-*/` (chmod 0600) |

## Arquitetura embedded mode (rail de seções)

```
┌─────────────────────────────────────────────────────────┐
│ VigiaOS (Adw.Application, application_id=br.com.vigia.OS)│
│                                                         │
│ ┌────────────┐ ┌──────────────┐ ┌────────────────────┐ │
│ │ Rail       │ │ Sidebar      │ │ Content Stack      │ │
│ │ - Início   │ │ (no Hub)     │ │ Embedded tools via │ │
│ │ - Hub      │ │ Categorias:  │ │ build_content():   │ │
│ │ - Red      │ │ - Monitor.   │ │   Gtk.Widget       │ │
│ │ - Blue     │ │ - Privac.    │ │                    │ │
│ │ ────────── │ │ - Defesa     │ └────────────────────┘ │
│ │ - Config.  │ │ - Sistema    │                        │
│ │ - 🔔       │ │ - Reports    │                        │
│ └────────────┘ └──────────────┘                        │
└─────────────────────────────────────────────────────────┘
```

O rail troca de **seção**; **Início** é a landing (monitor do sistema).
Em Hub/Red/Blue, a sidebar lista os módulos por categoria e cada tool
exporta `build_content() -> Gtk.Widget`, embedded diretamente no
`Gtk.Stack` — navegação sem spawnar processos separados. Red/Blue
reaproveitam o mesmo master-detail via adaptador `Module → ToolEntry`.
No rodapé do rail: **Configurações** (abas Sobre · Atualizações ·
Aplicação · Segurança · Ajuda) e o sino de **Notificações**.

## Comunicação tray ↔ app

```
[VigiaOS GTK4] ←── D-Bus session bus ───→  [vigia-hub-tray GTK3]
   │                                              │
   │ application_id = "br.com.vigia.OS"           │
   │ Gio.SimpleAction:                            │
   │   - show-window                              │
   │   - show-settings                            │
   │   - quit-hub                                 │
   │                                              │
   └─ spawn (Popen + PR_SET_PDEATHSIG) ──→ Tray subprocess
                                              │
                                              └─ AyatanaAppIndicator3
                                                 + Gtk.Menu (GTK3)
```

GTK3 e GTK4 não coexistem num mesmo processo PyGObject — daí a
separação em subprocess.

## Diretórios de configuração

| Path | Conteúdo | Permissão |
|---|---|---|
| `~/.config/vigia-hub/settings.json` | App (casca): autostart, tray, lock, theme | 0600 |
| `~/.config/autostart/vigia-hub.desktop` | XDG autostart entry | 0644 |
| `~/.config/vigia-dns/state.json` | DNS Manager: servidor ativo | 0600 |
| `~/.config/vigia-dashboard/alerts.json` | Dashboard: alertas configurados | 0600 |
| `~/.local/share/vigia-reports/` | Relatórios gerados (PDF/HTML) | 0700 dir |

## Categorias e tools

### 📡 Monitoramento
- **Dashboard** — Sistema em tempo real (CPU/RAM/disco/rede/processos)
- **Activity Log** — Auditoria de eventos (audit + journald + fail2ban)
- **Network Monitor** — Conexões TCP/UDP em tempo real

### 🔒 Privacidade
- **Privacy Controls** — 12 toggles GNOME (location, telemetria, etc)
- **DNS Manager** — `dnscrypt-proxy` (DoH/DoT) com servidores curados

### 🛡️ Defesa & Hardening
- **SELinux Manager** — Booleans, denials, restorecon, audit2allow
- **Firewall Manager** — `firewalld` zones + serviços
- **Hardening Checks** — Wrapper `lynis`
- **File Integrity** — AIDE (sistema) + hash ad-hoc (user)
- **Capabilities Inspector** — `getcap` audit + 41 caps documentadas
- **Antivirus** — Wrapper ClamAV (substitui clamtk)
- **Rootkit Scanner** — `chkrootkit` + `rkhunter` unificados

### ⚙️ Sistema
- **Atualizações** — Checa/aplica updates do sistema + suíte via `dnf`
  (aba em Configurações; antigo "Tool Installer")

### 📋 Relatórios
- **Reports** — PDF/HTML LGPD via Activity Log JSON

## Padrões de código

- **GTK4 + libadwaita 1**: `Adw.ApplicationWindow`, `Adw.PreferencesPage`,
  `Adw.NavigationSplitView`, `Adw.ViewSwitcher`
- **`pkexec` (NUNCA sudo)**: privilege escalation via Polkit
- **State JSON com atomic write**: `tmp.replace(final)` + `chmod 0600`
- **Subprocess async**: `Gio.Subprocess.communicate_utf8_async` (evita
  bloquear UI)
- **Tests com pytest**: 383+ casos cobrindo backend, helpers, parsers

## Workflow de desenvolvimento

```bash
# Setup numa máquina nova
git clone https://github.com/andre28abr/VigiaOS.git ~/dev/VigiaOS
cd ~/dev/VigiaOS
(cd tools/vigia-common && pip install --user -e .)
for d in vigia-hub privacy-controls selinux-gui firewall-gui ...; do
  (cd tools/$d && pip install --user -e .)
done
vigia-os  # abre o app (aliases: vigia-hub / vigia-blue / vigia-red)
```

## Distribuição futura (COPR)

Specs RPM prontas em `packaging/`:
- `vigia-suite.spec` (metapackage)
- `vigia-common.spec` (lib noarch)
- 17 spec files por tool

```bash
sudo dnf install vigia-suite
```
