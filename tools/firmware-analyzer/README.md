# Vigia Firmware Analyzer

GUI moderna para `binwalk` — análise de firmware, imagens de disco e
binários genéricos. Útil para reverse engineering e auditoria de
dispositivos.

## Status

v0.1.0 — alpha. Análise de signatures + extração de embeded files +
gráfico de entropia (ASCII).

## Features

- **Análise de signatures**: detecta arquivos embarcados (JPEG, ZIP,
  filesystems, kernel images) num blob binário
- **Extração**: extrai todos os embeded files para diretório de output
- **Entropia**: identifica regiões de dados compactados/criptografados
  (entropia alta) vs. dados estruturados (entropia baixa)
- **Histórico** em `~/.local/share/vigia-firmware/` (permissões `0600`)
- **Aba Sobre** com manual didático e contexto de uso

## Setup

```bash
sudo rpm-ostree install binwalk
systemctl reboot
pip install --user -e .
vigia-firmware
```

## Wrapper de

- `binwalk`

## Roadmap

- v0.2: visualização gráfica de entropia (Cairo)
- v0.2: filesystem analysis para imagens (squashfs, ext)
- v0.3: comparativo de firmware (delta entre versões)
