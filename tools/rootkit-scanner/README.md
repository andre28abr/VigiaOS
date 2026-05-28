# Vigia Rootkit Scanner

Wrapper unificado de **chkrootkit** + **Rootkit Hunter** com UI GTK4.
Parte da [Vigia Suite](../../README.md).

v0.2.0: reescrito do zero usando pattern identico ao Antivirus.

## O que faz

- **chkrootkit tab** — scan rapido (~30s)
- **Rootkit Hunter tab** — scan completo (2-5min)
- **Historico tab** — lista de scans anteriores
- **Sobre tab** — manual didatico

## Pre-requisitos

- `chkrootkit` instalado (rpm-ostree install chkrootkit)
- `rkhunter` instalado (rpm-ostree install rkhunter)

Use o **Vigia Tool Installer** pra instalacao 1-click.

## Como rodar

Normalmente embedded no **Vigia Hub**:
```bash
vigia-hub
```

Standalone:
```bash
cd tools/rootkit-scanner
pip install --user -e .
vigia-rootkit
```

## LGPD

Reports JSON em `~/.local/share/vigia-rootkit/scans/` com mode 0600.
