# Visão geral do VigiaOS (técnico)

## O que é

VigiaOS é uma **suite de 16 ferramentas GTK4 + libadwaita** focada em
segurança, privacidade e conformidade com LGPD para Fedora Silverblue
(e derivadas atômicas: Kinoite, Bluefin, Bazzite, Aurora).

Não é uma distribuição Linux — é um **toolkit** que roda sobre
Silverblue vanilla, aproveitando a base atômica oficial da Red Hat.

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

## Arquitetura embedded mode (Hub)

```
┌─────────────────────────────────────────────────────────┐
│ Vigia Hub (Adw.Application, application_id=br.com...)   │
│                                                         │
│ ┌────────────┐ ┌──────────────┐ ┌────────────────────┐ │
│ │ Nav fina   │ │ Sidebar      │ │ Content Stack      │ │
│ │ - Tools    │ │ Categorias:  │ │ Embedded tools via │ │
│ │ - Inst.    │ │ - Monitor.   │ │ build_content():   │ │
│ │ - Config.  │ │ - Privac.    │ │   Gtk.Widget       │ │
│ │ - Ajuda    │ │ - Defesa     │ │                    │ │
│ └────────────┘ │ - Sistema    │ └────────────────────┘ │
│                │ - Reports    │                        │
│                └──────────────┘                        │
└─────────────────────────────────────────────────────────┘
```

Cada tool exporta `build_content() -> Gtk.Widget` que é embedded
diretamente no `Gtk.Stack` do Hub. Permite navegação sem spawnar
processos separados.

## Comunicação tray ↔ Hub

```
[Hub GTK4]  ←─── D-Bus session bus ───→  [vigia-hub-tray GTK3]
   │                                              │
   │ application_id = "br.com.vigia.Hub"          │
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
| `~/.config/vigia-hub/settings.json` | Hub: autostart, tray, lock, theme | 0600 |
| `~/.config/autostart/vigia-hub.desktop` | XDG autostart entry | 0644 |
| `~/.config/vigia-deployments/state.json` | Labels + notas dos deployments | 0600 |
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
- **Hardening Checks** — Wrapper `lynis` + perfil Silverblue
- **File Integrity** — AIDE (sistema) + hash ad-hoc (user)
- **Capabilities Inspector** — `getcap` audit + 41 caps documentadas
- **Antivirus** — Wrapper ClamAV (substitui clamtk)
- **Rootkit Scanner** — `chkrootkit` + `rkhunter` unificados

### ⚙️ Sistema
- **Tool Installer** — Catálogo `rpm-ostree` + extensões browser FOSS
- **Deployments Manager** — `rpm-ostree` GUI (rollback, pin, cleanup)

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
vigia-hub  # abre o launcher
```

## Distribuição futura (COPR)

Specs RPM prontas em `packaging/`:
- `vigia-suite.spec` (metapackage)
- `vigia-common.spec` (lib noarch)
- 17 spec files por tool

```bash
sudo rpm-ostree install vigia-suite
sudo systemctl reboot
```
