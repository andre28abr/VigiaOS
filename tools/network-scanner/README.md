# Vigia Network Scanner

GUI moderna para `nmap` — descoberta de hosts e scan de portas com
perfis pré-definidos.

## Status

v0.1.0 — alpha. Funcional para discovery (ping scan) e port scan
standard/aggressive. Resultados parseados de XML do nmap.

## Features

- **Perfis pré-definidos** (Discovery, Quick, Standard, Aggressive, Full, Stealth)
- **Parse XML do nmap** — hosts + portas + serviços + OS guess
- **Modo admin opt-in** para scans que precisam de root (SYN, OS detection)
- **Histórico** de scans em `~/.local/share/vigia-netscan/` (permissões `0600`)
- **Validação de targets** — aceita IP, hostname, CIDR
- **Aba Sobre** com manual didático e contexto de uso ético/legal

## Setup

```bash
sudo rpm-ostree install nmap
systemctl reboot
pip install --user -e .
vigia-netscan
```

## Wrapper de

- `nmap`

## Uso ético

Scan de redes sem autorização é **crime em vários países**. Use apenas em:
- Sua própria rede doméstica/empresarial
- Sistemas para os quais você tem autorização escrita
- Targets de CTF/laboratório

## Roadmap

- v0.2: gráfico de topologia
- v0.2: integração com Capabilities Inspector (detectar serviços com caps)
- v0.3: scripts NSE selecionáveis
