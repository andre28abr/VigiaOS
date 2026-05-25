# Vigia DNS Manager

Gerenciador de DNS via **systemd-resolved** com catalogo de provedores curado e DoT (DNS over TLS). Parte da [Vigia Suite](../../README.md).

## O que faz

- **Status**: detecta provedor em uso, mostra DNS configurado, DoT habilitado, interfaces, status do systemd-resolved
- **Provedores**: catalogo de ~9 DNS publicos (Cloudflare, Quad9, AdGuard, Mullvad, Google, etc.) com descricao + filtros + 1-click apply
- **DoT toggle**: encripta queries entre voce e o resolver
- **Backup automatico** do `/etc/systemd/resolved.conf` antes de aplicar
- **Flush cache** + **Restaurar config padrao** quando precisar voltar atras

## Pre-requisitos

- `systemd-resolved` (default em Fedora Silverblue desde F32)
- `resolvectl` (vem com systemd)

Confirma:
```bash
systemctl is-active systemd-resolved
which resolvectl
```

## Como rodar

```bash
cd tools/dns-manager
pip install --user -e .
vigia-dns
```

Ou via Vigia Hub.

## Provedores no catalogo

| Provedor | IPs | Filtros |
|----------|-----|---------|
| **Cloudflare** | 1.1.1.1, 1.0.0.1 | (nenhum) |
| **Cloudflare Malware** | 1.1.1.2, 1.0.0.2 | malware |
| **Cloudflare Family** | 1.1.1.3, 1.0.0.3 | malware + adulto |
| **Quad9** | 9.9.9.9, 149.112.112.112 | malware |
| **AdGuard DNS** | 94.140.14.14, 94.140.15.15 | ads + trackers |
| **AdGuard Family** | 94.140.14.15, 94.140.15.16 | ads + trackers + adulto |
| **Mullvad DNS** | 194.242.2.2, 194.242.2.3 | (nenhum, no-logs) |
| **Mullvad AdBlock** | 194.242.2.3, 194.242.2.4 | ads + trackers + malware |
| **Google Public DNS** | 8.8.8.8, 8.8.4.4 | (nenhum) |

## Estrutura

```
tools/dns-manager/
├── pyproject.toml
├── data/
│   ├── br.com.vigia.DnsManager.svg
│   └── br.com.vigia.DnsManager.desktop
└── src/vigia_dns/
    ├── __init__.py / __main__.py / app.py
    ├── backend.py          # resolvectl status + /etc/systemd/resolved.conf
    ├── resolvers.py        # catalogo de provedores
    ├── window.py           # 3 tabs (Status + Provedores + Sobre)
    └── tabs/
        ├── _helpers.py
        ├── status.py       # hero + global + interfaces + flush/restore
        ├── resolvers.py    # ExpanderRow por provedor + Apply
        └── about.py
```

## Limitacoes v0.1

- DoH (DNS over HTTPS) nao suportado (systemd-resolved nao tem DoH nativo). Use Cloudflare Family no Firefox para isso.
- Blocklists locais tipo Pi-hole nao estao na v0.1. Use AdGuard DNS ou Mullvad AdBlock que ja filtram no servidor.
- NetworkManager pode sobrescrever o DNS por interface — veja a aba Status pra confirmar.

## Roadmap (v0.2+)

- Integracao com dnscrypt-proxy (suporta DoH + blocklists locais)
- Custom resolver (paste IP manualmente)
- Blocklists tipo Pi-hole (via dnscrypt-proxy cloaking)
- Teste de latencia em todos os resolvers do catalogo (botao "Recomendar mais rapido")
- Indicador na nav lateral do Hub (verde quando DoT ativo)
