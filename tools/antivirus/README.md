# Vigia Antivirus

Antivirus on-demand para Linux desktop, com UI GTK4 moderna. Wrapper de
ClamAV — substitui o `clamtk` (que tem UI envelhecida e quebra com
frequência no GTK4).

## Status

v0.1.0 — alpha. Funcional para scan on-demand, update de base de assinaturas
e visualização de findings.

## Features

- **Scan on-demand** de arquivo, diretório ou home completo
- **Progress streaming** durante scan (não trava UI)
- **Catálogo de assinaturas** com data do último update e contagem
- **Update de base** via `pkexec freshclam` (1 dialog)
- **Detecção de daemon** `clamd`/`clamav-daemon` (acelera scan se estiver rodando)
- **Histórico de scans** em `~/.local/share/vigia-antivirus/` (permissões `0600`)
- **Aba Sobre** com manual didático

## Setup

```bash
sudo rpm-ostree install clamav clamav-update clamav-server
systemctl reboot
# Primeira vez: atualizar base
sudo freshclam
# Ou usar a UI:
pip install --user -e .
vigia-antivirus
```

## Wrapper de

- `clamav` (binário `clamscan`)
- `clamav-update` (binário `freshclam`)

## Roadmap

- v0.2: scheduled scans (systemd timer)
- v0.2: scan em background com daemon `clamd` ativo (clamdscan, mais rápido)
- v0.3: quarentena visual
- v0.3: integração com Activity Log
