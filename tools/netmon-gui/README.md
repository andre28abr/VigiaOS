# Vigia Network Monitor

> Monitor visual de conexões TCP/UDP em tempo real. Wrapper GTK4 sobre `ss`.

## Estado

🟡 **v0.1 MVP** — duas tabs com auto-refresh:

### Conexões
- **Todas** as conexões TCP+UDP em qualquer estado (ESTAB, LISTEN, TIME-WAIT, UNCONN, etc.)
- Ordenado: ESTAB → LISTEN → resto, depois por nome de processo
- **State badge** colorido: ESTAB verde, LISTEN accent, WAIT/SENT amber
- **Auto-refresh** a cada 3s (toggle ON/OFF + botão "Atualizar")
- **Search/filter** por processo, IP, porta, estado

### Listening
- Apenas sockets em **LISTEN** (TCP server) ou **UNCONN** com peer wildcard (UDP server)
- Mesma UI, mesmo auto-refresh
- Crítico para segurança: lista TUDO que aceita conexões neste host

## Setup

```bash
cd ~/dev/VigiaOS/tools/netmon-gui
pip install --user -e .
vigia-netmon
```

Para entry no menu GNOME:
```bash
mkdir -p ~/.local/share/applications ~/.local/share/icons/hicolor/scalable/apps
cp data/br.com.vigia.NetMon.desktop ~/.local/share/applications/
cp data/br.com.vigia.NetMon.svg ~/.local/share/icons/hicolor/scalable/apps/
gtk-update-icon-cache ~/.local/share/icons/hicolor 2>/dev/null || true
update-desktop-database ~/.local/share/applications 2>/dev/null || true
```

## Sobre root

Sem root, `ss -tunap` **não mostra process info** de sockets de outros usuários
(você verá `(processo restrito)`). Para visibility completa:

```bash
sudo vigia-netmon
```

Aí TODOS os sockets de todos os usuários mostram nome+PID.

## Limitações v0.1

- **Sem DNS reverse lookup** — mostra IPs em vez de hostnames (mais rápido, mais seguro)
- **Sem stats de bandwidth** — `iftop`/`nethogs` integration em v0.2
- **Sem deep packet inspection** — só estatísticas de sockets
- **Sem históricos** — view é instantânea (refresh substitui)
- **Sem filtros por categoria** (ex: "só HTTPS", "só local") — v0.2

## Roadmap

- ✅ v0.1: Connections + Listening tabs com auto-refresh
- v0.2: DNS reverse lookup opcional (async em background), bandwidth por processo
- v0.3: Históricos curtos (5min back), gráficos de throughput
- v0.4: Integração com Firewall GUI ("bloquear esse IP") e Activity Log ("ver logs deste processo")
- v0.5: Filtros pré-definidos: "Só HTTPS", "Só local", "Suspeitos" (porta não-padrão, processo unknown)

## Stack

- Python 3.11+ + PyGObject + GTK4 + libadwaita
- Backend: parser de `ss -tunap` output
- Sem deps externas pip (PyGObject vem do RPM `python3-gobject`)
