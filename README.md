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

## O que está incluído (v2 em desenvolvimento)

| Componente | Status | Função |
|---|---|---|
| `bootstrap.sh` | 🟡 Em desenvolvimento | Script one-liner que instala ferramentas essenciais de segurança/privacidade/dev em Silverblue vanilla |
| **[Vigia Hub](tools/vigia-hub/)** | 🟡 v0.1 MVP | Launcher mestre da suite — 1 ícone no GNOME que lista e abre todas as ferramentas. Python + GTK4. |
| **[Vigia Activity Log](tools/activity-log/)** | 🟢 v0.7 funcional | Parser de audit + journald + fail2ban com narrativa human-readable, correlations cross-source, classificador de severidade, live tail mode |
| **[Vigia Privacy Controls](tools/privacy-controls/)** | 🟢 v0.3 funcional | App GTK4 com 13 toggles (10 user-scope dconf + 3 system-scope via pkexec: firewall, SSH, Tor). Python + PyGObject + libadwaita. |
| Vigia Control Center | ⚪ Futuro | App GTK4 central — tabs de ferramentas, privacidade, SELinux, logs |
| SELinux GUI moderno | ⚪ Futuro | Substituto de `system-config-selinux` em GTK4 |
| Tema VigiaOS (opcional) | ⚪ Futuro | Script aplicador do tema zinc + emerald (do app SentinelBR) |

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
