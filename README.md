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

## O que está incluído (v2 — 15 ferramentas funcionais)

| # | Componente | Stack | Status |
|---|---|---|---|
| 1 | `bootstrap.sh` | bash | 🟡 Em desenvolvimento |
| 2 | **[Vigia Hub](tools/vigia-hub/)** v0.5 | Python + GTK4 | 🟢 3 painéis (nav fina + sidebar categorizada + content), embedded mode |
| 3 | **[Vigia Activity Log](tools/activity-log/)** v0.7 (core) + [GUI](tools/activity-log-gui/) v0.1 | Rust + Python | 🟢 audit + journald + fail2ban + correlations |
| 4 | **[Vigia Privacy Controls](tools/privacy-controls/)** v0.3 | Python + GTK4 | 🟢 13 toggles user+system scope |
| 5 | **[Vigia SELinux GUI](tools/selinux-gui/)** v0.2 | Python + GTK4 | 🟢 6 tabs + pt-BR + audit2allow |
| 6 | **[Vigia Firewall GUI](tools/firewall-gui/)** v0.1 | Python + GTK4 | 🟡 Status + zones CRUD |
| 7 | **[Vigia Network Monitor](tools/netmon-gui/)** v0.1 | Python + GTK4 | 🟡 Conexões + modo admin opt-in |
| 8 | **[Vigia Hardening Checks](tools/hardening-checks/)** v0.1.2 | Python + GTK4 | 🟢 Lynis wrapper + perfil Silverblue |
| 9 | **[Vigia Reports](tools/reports/)** v0.1.1 | Python + Jinja2 + WeasyPrint | 🟢 PDF/HTML LGPD |
| 10 | **[Vigia File Integrity](tools/file-integrity/)** v0.1.3 | Python + GTK4 | 🟢 AIDE wrapper + perfil Silverblue |
| 11 | **[Vigia Tool Installer](tools/tool-installer/)** v0.1 | Python + GTK4 | 🟢 Catálogo via `rpm-ostree install` |
| 12 | **[Vigia VPN Manager](tools/vpn-manager/)** v0.1.1 | Python + GTK4 | 🟢 WireGuard wrapper |
| 13 | **[Vigia DNS Manager](tools/dns-manager/)** v0.1 | Python + GTK4 | 🟢 systemd-resolved + 9 providers DoT |
| 14 | **[Vigia Capabilities Inspector](tools/capabilities-inspector/)** v0.1 | Python + GTK4 | 🟢 getcap audit + 41 caps pt-BR |
| 15 | **[Vigia Antivirus](tools/antivirus/)** v0.1 | Python + GTK4 | 🟢 ClamAV wrapper (substitui clamtk) |
| 16 | **[Vigia Network Scanner](tools/network-scanner/)** v0.1 | Python + GTK4 | 🟢 nmap GUI com 6 perfis |
| 17 | **[Vigia Firmware Analyzer](tools/firmware-analyzer/)** v0.1 | Python + GTK4 | 🟢 binwalk: signatures + extract + entropia |
| 18 | **[Vigia Hash Tools](tools/hash-tools/)** v0.1 | Python + GTK4 | 🟢 SHA-256/512, baseline+diff |

## Instalação rápida (quando bootstrap.sh estiver pronto)

Em qualquer Fedora Silverblue (ou Kinoite/Bluefin/etc.) já instalado:

```bash
curl -fsSL https://raw.githubusercontent.com/andre28abr/VigiaOS/main/bootstrap.sh | bash
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
