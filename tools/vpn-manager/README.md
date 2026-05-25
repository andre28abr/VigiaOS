# Vigia VPN Manager

Gerenciador grafico de perfis **WireGuard** com UI GTK4. Parte da [Vigia Suite](../../README.md).

## O que faz

- Lista perfis em `/etc/wireguard/*.conf` (read via `pkexec`)
- **Conectar / Desconectar** via `pkexec wg-quick up/down`
- **Importar** novo perfil (paste do conteudo .conf via dialog)
- **Status detalhado**: peers conectados, handshake, dados transferidos
- Cada operacao = 1 dialog polkit. Sem terminal.

## Pre-requisitos

```bash
rpm-ostree install wireguard-tools
systemctl reboot
```

Em Silverblue, `/etc/wireguard/` e' criado automaticamente com mode 0700 ao instalar `wireguard-tools`.

## Como rodar

```bash
cd tools/vpn-manager
pip install --user -e .
vigia-vpn
```

Ou via Vigia Hub.

## Estrutura

```
tools/vpn-manager/
├── pyproject.toml
├── data/
│   ├── br.com.vigia.VpnManager.svg
│   └── br.com.vigia.VpnManager.desktop
└── src/vigia_vpn/
    ├── __init__.py / __main__.py / app.py
    ├── backend.py         # wg-quick + wg show wrappers
    ├── window.py          # 3 tabs (Status + Perfis + Sobre)
    └── tabs/
        ├── _helpers.py
        ├── status.py      # hero + interfaces ativas + peers
        ├── profiles.py    # lista perfis + connect/disconnect/import
        └── about.py
```

## Fluxo tipico

1. **Importar perfil** (uma vez por VPN): aba *Perfis* > *Importar novo* > cola conteudo .conf
2. **Conectar**: aba *Perfis* > clica *Conectar* no perfil desejado
3. **Ver status**: aba *Status* > *Detalhes (admin)* para ver peers/handshake/bytes
4. **Desconectar**: aba *Perfis* > clica *Desconectar*

## Limitacoes v0.1

- Apenas WireGuard (OpenVPN vira em v0.2)
- Sem auto-connect no boot (usar `systemctl enable wg-quick@<nome>` manualmente)
- Sem editor visual do .conf — para editar, abre arquivo em terminal

## Roadmap (v0.2+)

- Suporte OpenVPN (`openvpn3-linux`)
- Editor visual do .conf (form com fields)
- Auto-connect toggle via systemd
- Indicador de status na nav lateral do Hub (verde quando conectado)
- Lista de servidores VPN populares (Mullvad, ProtonVPN) com import 1-click
