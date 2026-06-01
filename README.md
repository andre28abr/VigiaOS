# VigiaOS &nbsp; — Suite de segurança para Fedora Silverblue

> **VigiaOS não é uma distro Linux.** É uma coleção de ferramentas, scripts e
> aplicativos gráficos que transformam uma instalação **vanilla** de Fedora
> Silverblue em uma estação de trabalho voltada para segurança, privacidade,
> auditoria e conformidade com LGPD.

## Por que não uma distro?

Manter uma distro custom é caro (segurança, updates, testes contra upstream).
Manter ferramentas é leve. Red Hat já constrói um ótimo OS atômico —
deixamos eles fazerem isso e construímos por cima.

Resultado: as ferramentas funcionam em qualquer Fedora Atomic (Silverblue,
Kinoite, Bluefin, Bazzite, Aurora), aproveitando atualizações automáticas
do sistema-base sem complicação.

## O que está incluído (v2 — 16 ferramentas focadas em LGPD/escritório)

| # | Componente | Stack | Status |
|---|---|---|---|
| 1 | `bootstrap.sh` | bash | 🟡 Em desenvolvimento |
| 2 | **[Vigia Hub](tools/vigia-hub/)** v0.7.4 | Python + GTK4 | 🟢 3 painéis + autostart XDG + tray (quick actions) + lock Polkit + backup/restore + Ajuda (manuais MD) |
| 3 | **[Vigia Monitor do Sistema](tools/dashboard/)** v0.4.1 | Python + GTK4 + Cairo | 🟢 Sistema em tempo real + per-process I/O + alertas + inspetor syscalls + banda por processo + selo de plataforma |
| 4 | **[Vigia Activity Log](tools/activity-log/)** v0.7.1 (core) + [GUI](tools/activity-log-gui/) v0.1 | Rust + Python | 🟢 audit + journald + fail2ban + correlations |
| 5 | **[Vigia Privacy Controls](tools/privacy-controls/)** v0.3.1 | Python + GTK4 | 🟢 13 toggles user+system scope |
| 6 | **[Vigia SELinux GUI](tools/selinux-gui/)** v0.2 | Python + GTK4 | 🟢 6 tabs + pt-BR + audit2allow |
| 7 | **[Vigia Firewall GUI](tools/firewall-gui/)** v0.1 | Python + GTK4 | 🟡 Status + zones CRUD |
| 8 | **[Vigia Network Monitor](tools/netmon-gui/)** v0.1.1 | Python + GTK4 | 🟡 Conexões + modo admin opt-in |
| 9 | **[Vigia Hardening Checks](tools/hardening-checks/)** v0.1.4 | Python + GTK4 | 🟢 Lynis wrapper + perfil Silverblue |
| 10 | **[Vigia Reports](tools/reports/)** v0.2.6 | Python + Jinja2 + SVG | 🟢 6 modelos + selo SHA-256 + identidade do escritório + **agendamento mensal** (headless) |
| 11 | **[Vigia File Integrity](tools/file-integrity/)** v0.2.4 | Python + GTK4 | 🟢 AIDE (sistema) + Hash ad-hoc (user) — 6 tabs |
| 12 | **[Vigia Tool Installer](tools/tool-installer/)** v0.3.3 | Python + GTK4 | 🟢 rpm-ostree + **extensões navegador open source** |
| 13 | **[Vigia DNS Manager](tools/dns-manager/)** v0.4.2 | Python + GTK4 | 🟢 **dnscrypt-proxy** (DoH/DoT) com 11 servers curados |
| 14 | **[Vigia Capabilities Inspector](tools/capabilities-inspector/)** v0.1 | Python + GTK4 | 🟢 getcap audit + 41 caps pt-BR |
| 15 | **[Vigia Antivirus](tools/antivirus/)** v0.1.1 | Python + GTK4 | 🟢 ClamAV wrapper (substitui clamtk) |
| 16 | **[Vigia Rootkit Scanner](tools/rootkit-scanner/)** v0.2.0 | Python + GTK4 | 🟢 **chkrootkit + rkhunter** unificados |
| 17 | **[Vigia Deployments Manager](tools/deployments-manager/)** v0.1.1 | Python + GTK4 | 🟢 **rpm-ostree** GUI — rollback, pin, cleanup, labels LGPD |

### Removidas na limpeza 2026-05-27 (foco LGPD)

- ~~Network Scanner (nmap)~~ — fora do escopo + risco ético (Lei 12.737/12)
- ~~Firmware Analyzer (binwalk)~~ — nicho RE/CTF
- ~~VPN Manager~~ — NetworkManager nativo do GNOME já gerencia WireGuard
- ~~Hash Tools~~ — mergeado em File Integrity v0.2.0 (mesma categoria)

### Novidades do Hub v0.7.1 (2026-05-29)

Além das **Configurações** (centro de preferências com 3 sub-abas, abaixo), as
versões v0.6–v0.7 adicionaram a aba **Ajuda** (manuais em Markdown renderizados
in-app), **ações rápidas na bandeja** (submenu "Abrir módulo" → Monitor do Sistema,
Antivírus, etc.) e **backup/restauração** da config em `.zip` (0600, LGPD).

A aba **Configurações** do Hub virou um centro real de preferências, com 3 sub-abas:

- **Aplicação**
  - ✅ **Autostart XDG** — switch "Iniciar junto com o sistema" cria `~/.config/autostart/vigia-hub.desktop`
  - ✅ **Tray icon** — switch "Mostrar ícone na bandeja" spawna subprocess GTK3 (`vigia-hub-tray`) que cria ícone no menu de status do GNOME via `AyatanaAppIndicator3`. Menu minimalista: Abrir Hub / Configurações / Sair
  - ✅ **Iniciar minimizado** — flag `--minimized` no autostart; Hub sobe só com tray, janela escondida
  - **Background mode** automático: fechar a janela (X) com tray ativo esconde em vez de matar o processo (`app.hold()`)
- **Segurança**
  - ✅ **Bloqueio por senha (Polkit)** — switch "Exigir senha para abrir o Hub". Usa `pkexec /usr/bin/true` via `Gio.Subprocess` async. Zero armazenamento de credencial (LGPD friendly). **Lazy auth**: se Hub iniciar minimizado, senha só é pedida quando user clicar "Abrir Hub" no tray (não interrompe o login)
- **Sobre** — caminhos de configuração + versão

## Instalação

### Tudo de uma vez (recomendado)

Um comando — o instalador **detecta sozinho** se você está em Fedora
Atomic (Silverblue, Kinoite, Bluefin, Bazzite, Aurora) ou Workstation, e
usa `rpm-ostree` ou `dnf`:

```bash
curl -fsSL https://raw.githubusercontent.com/andre28abr/VigiaOS/main/install/bootstrap.sh | bash
# Em sistema atômico, reinicie ao final:  systemctl reboot
```

Instala as 16 ferramentas + os backends que elas usam (`lynis`, `aide`,
`clamav`, …), registra os atalhos no menu do GNOME e instala Flatpaks de
privacidade (KeePassXC, Signal, Tor Browser…). **Não liga nenhum serviço**
— `fail2ban`/`dnscrypt-proxy` ficam off; você ativa cada um na
ferramenta correspondente (*minimum surface area* / LGPD). Guias por
plataforma: **[Silverblue / atomic](install/silverblue/)** ·
**[Workstation](install/workstation/)**.

### Instalar só um módulo (isolado)

Não precisa da suíte inteira. Para usar **uma ferramenta só** (ex: só o
Antivírus), use o helper — instala a tool no seu usuário (`pip --user`,
**sem root**) e registra o atalho + ícone no GNOME. Funciona igual em
Silverblue e Workstation:

```bash
git clone https://github.com/andre28abr/VigiaOS.git ~/dev/VigiaOS
cd ~/dev/VigiaOS
install/install-tool.sh --list          # ver módulos disponíveis
install/install-tool.sh antivirus       # instala só o Antivírus
```

Cada módulo roda sozinho, sem depender do Vigia Hub. Quando o COPR estiver
ativo: `rpm-ostree install vigia-antivirus` (atomic) ou `dnf install
vigia-antivirus` (Workstation).

### Compatibilidade por plataforma

Quase tudo roda igual nos dois — as diferenças:

| | Silverblue / Atomic | Workstation |
|---|---|---|
| Pacotes | `rpm-ostree` (+ reboot) | `dnf` (na hora) |
| Deployments Manager | ✅ | ❌ (sem deployments rpm-ostree) |
| Tool Installer → aba *Pendentes* | ✅ | ❌ (instala na hora) |
| As outras 15 ferramentas | ✅ | ✅ |

### Dev (editable)

Para hackear no código, instale em editable mode (roteiro completo em
[DEVELOPMENT.md §8](DEVELOPMENT.md#8-setup-numa-máquina-nova-silverblue-limpa)):

```bash
git clone https://github.com/andre28abr/VigiaOS.git ~/dev/VigiaOS
cd ~/dev/VigiaOS
(cd tools/vigia-common && pip install --user -e .)   # dep das outras, primeiro
for d in vigia-hub privacy-controls selinux-gui firewall-gui netmon-gui \
         hardening-checks reports file-integrity tool-installer \
         dns-manager capabilities-inspector activity-log-gui \
         antivirus dashboard rootkit-scanner deployments-manager; do
  (cd tools/$d && pip install --user -e .)
done
vigia-hub   # abre o launcher
```

### Futuro: via COPR (em preparação)

As specs RPM estão prontas em [`packaging/`](packaging/), mas o **repo
COPR ainda não foi ativado** (passos em [`packaging/README.md`](packaging/README.md)).
Quando ativo:

```bash
sudo wget -O /etc/yum.repos.d/_copr_andre28abr-vigia.repo \
  https://copr.fedorainfracloud.org/coprs/andre28abr/vigia/repo/fedora-$(rpm -E %fedora)/andre28abr-vigia-fedora-$(rpm -E %fedora).repo
sudo rpm-ostree install vigia-suite && sudo systemctl reboot   # atomic
# Workstation: sudo dnf copr enable andre28abr/vigia && sudo dnf install vigia-suite
```

## Histórico

A v1 do projeto era uma distro Linux completa baseada em Fedora Silverblue
buildada via BlueBuild. Foi pivotada em 2026-05-22 para suíte de ferramentas
após avaliarmos que o trabalho de manter um image build sobrepunha pouco
valor ao que Red Hat já entrega. A v1 está preservada em
[`legacy/v1-distro`](https://github.com/andre28abr/VigiaOS/tree/legacy/v1-distro).

## Documentação

- [DEVELOPMENT.md](DEVELOPMENT.md) — arquitetura, decisões, roadmap

## Licença

Apache 2.0 — ver [LICENSE](LICENSE).
