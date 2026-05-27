# Vigia DNS Manager

Gerenciador de DNS focado em **privacidade**, wrappa o `dnscrypt-proxy`.
Parte da [Vigia Suite](../../README.md).

## O que faz

- **Status**: estado do dnscrypt-proxy, versao, server ativo, DNSSEC,
  no-logs. Botao 1-click para Ativar dnscrypt-proxy (apos instalacao
  via Tool Installer) ou Restaurar systemd-resolved padrao
- **Provedores**: catalogo de 11 servers dnscrypt-proxy curados
  (Cloudflare, Quad9, AdGuard, Mullvad, anonymized relay) com descricao
  + filtros + 1-click apply
- **Migracao 1-click** entre dnscrypt-proxy e systemd-resolved padrao

## Para bloqueio de ads/trackers

**Nao use DNS pra isso.** Use extensoes de navegador (uBlock Origin
e similares) que sao a ferramenta certa: escondem o elemento, anti-
anti-adblock, whitelist por site. DNS blocking deixa buraco no layout.

O **Vigia Tool Installer** tem aba **Extensoes de Navegador** com
recomendacoes open source (uBlock Origin, Privacy Badger, ClearURLs,
LibRedirect, etc.) — abre direto na AMO/Web Store do seu navegador.

## Pre-requisitos

- `dnscrypt-proxy` instalado:
  ```bash
  sudo rpm-ostree install dnscrypt-proxy
  systemctl reboot
  ```
  Ou via **Vigia Tool Installer** (recomendado).

## Como rodar

Normalmente embedded no **Vigia Hub**:
```bash
vigia-hub
# clique em "DNS Manager" na sidebar
```

Standalone (debugging):
```bash
cd tools/dns-manager
pip install --user -e .
vigia-dns
```

## Fluxo do primeiro uso

1. Abre a aba **Status**
2. Se `dnscrypt-proxy` esta instalado mas parado: clica em
   **"Ativar dnscrypt-proxy"** → confirma → senha admin
3. App faz backup do `systemd-resolved` config, para ele, aponta
   `/etc/resolv.conf` pra 127.0.0.1, sobe `dnscrypt-proxy`
4. Vai a **Provedores** e aplica um server (recomendado:
   **no-logs + DNSSEC** — Quad9 unfiltered ou Mullvad)
5. Para bloqueio de ads: instale **uBlock Origin** via aba "Extensoes
   de Navegador" do **Vigia Tool Installer**

## Como reverter (parar de usar)

Aba Status → **"Restaurar systemd-resolved padrao"**:
- Para dnscrypt-proxy (mantem o pacote instalado)
- Restaura `/etc/systemd/resolved.conf` do backup
- Restaura `/etc/resolv.conf` -> stub-resolv.conf
- Sobe systemd-resolved

## Catalogo de servers (11)

| Server | Provider | Protocolo | Features |
|--------|----------|-----------|----------|
| **Cloudflare** | Cloudflare | DoH | DNSSEC |
| **Cloudflare Security** | Cloudflare | DoH | DNSSEC + malware |
| **Cloudflare Family** | Cloudflare | DoH | DNSSEC + malware + adulto |
| **Quad9** | Quad9 | DoH | DNSSEC + malware + no-logs |
| **Quad9 (unfiltered)** | Quad9 | DoH | DNSSEC + no-logs |
| **AdGuard DNS** | AdGuard | DoH | DNSSEC + ads + trackers |
| **AdGuard Family** | AdGuard | DoH | DNSSEC + ads + trackers + adulto |
| **Mullvad** | Mullvad VPN | DoH | DNSSEC + no-logs |
| **Mullvad AdBlock** | Mullvad VPN | DoH | DNSSEC + no-logs + ads |
| **Quad9 DNSCrypt** | Quad9 | DNSCrypt | DNSSEC + no-logs |
| **Anonymized Relay** | (varios) | DNSCrypt + relay | no-logs + IP anonimo |

Ver `src/vigia_dns/dnscrypt_catalog.py` pra detalhes (jurisdicao, etc.).

## Estrutura

```
tools/dns-manager/
├── pyproject.toml
├── data/
│   ├── br.com.vigia.DnsManager.svg
│   └── br.com.vigia.DnsManager.desktop
└── src/vigia_dns/
    ├── __init__.py / __main__.py / app.py
    ├── dnscrypt_backend.py   # core: status, config TOML
    ├── dnscrypt_catalog.py   # 11 servers curados
    ├── migration.py          # setup helpers (ativar/restaurar)
    ├── window.py             # 3 tabs (Status, Provedores, Sobre)
    └── tabs/
        ├── _helpers.py
        ├── status.py         # hero + info + acoes
        ├── resolvers.py      # ExpanderRow por server + Apply
        ├── blocklists.py     # CRUD + import URL
        ├── stats.py          # KPIs + top dominios
        └── about.py
```

## v0.3.0 — breaking change da v0.2.x

A v0.2.x tinha "modo simples" (systemd-resolved) e "modo avancado"
(dnscrypt-proxy) como switch. A v0.3 **removeu o modo simples**.
Justificativas:

- Foco em privacidade (no-logs, DNSSEC, anonymized DNS)
- Blocklist e Stats so funcionam com dnscrypt — agora sempre disponiveis
- UI simples (1 catalogo, 1 backend, sem mode-aware bugs)
- 6 versoes consecutivas (v0.2.4 → v0.2.10) corrigindo bugs do mode-aware

Quem estava em "modo simples" ve o botao "Ativar dnscrypt-proxy" no
Status e faz migration em 1 click.

## LGPD/privacidade

- Query log desabilitado por default (regra `minimum-surface`)
- Quando habilitado, log fica LOCAL — nenhum dado vai pra rede
- Backups de config: `chmod 0600` (owner-only)
- Recomendado: usar servers com `no-logs` no catalogo (Quad9, Mullvad,
  Anonymized Relay)
