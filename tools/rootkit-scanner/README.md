# Vigia Rootkit Scanner

Wrapper unificado de **chkrootkit** + **Rootkit Hunter** com UI GTK4.
Parte do [VigiaOS](../../README.md).

v0.2.4 (a v0.2.0 foi reescrita do zero usando pattern identico ao Antivirus).

## O que faz

- **chkrootkit tab** — scan rapido (~30s)
- **Rootkit Hunter tab** — scan completo (2-5min)
- **Historico tab** — lista de scans anteriores
- **Sobre tab** — manual didatico

## Pre-requisitos

- `chkrootkit` instalado (sudo dnf install chkrootkit)
- `rkhunter` instalado (sudo dnf install rkhunter)

Ou rode `install/bootstrap.sh`, que instala os backends de todas as ferramentas.

## Como rodar

Normalmente embedded no **VigiaOS** (seção Hub):
```bash
vigia-os
```

Standalone:
```bash
cd tools/rootkit-scanner
pip install --user -e .
vigia-rootkit
```

## LGPD

Reports JSON em `~/.local/share/vigia-rootkit/scans/` com mode 0600.
