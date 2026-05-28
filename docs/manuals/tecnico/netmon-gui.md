# Network Monitor (netmon-gui)

## Em uma frase

Wrapper GTK4 do `ss -tunap` (socket statistics) com auto-refresh —
visualiza todas as conexões TCP/UDP ativas com nome do processo e PID,
em tempo real.

## O que envolve

| Item | Valor |
|---|---|
| **Pacotes Linux** | `iproute2` (fornece `ss`), `polkit` |
| **Comando principal** | `ss -tunap` (TCP+UDP, no DNS resolve, all states, process info) |
| **Permissões** | Read-only sem auth. Modo admin opt-in via `pkexec ss -tunap` para revelar processos system |
| **Stack** | Python 3.11+ · PyGObject · GTK4 · libadwaita 1 |
| **Path config** | Sem state local — coleta tudo em runtime |
| **App ID** | `br.com.vigia.NetMon` |
| **Versão** | 0.1.1 |

## Arquitetura interna

```
vigia_netmon/
├── backend.py     — list_connections(elevated=False) → list[NetConnection]
├── window.py      — build_content() monta ViewStack das 2 tabs
└── tabs/
    ├── connections.py — todas as conexões (TCP+UDP, qualquer estado)
    └── listening.py   — subclasse override que usa list_listening()
```

A tab Listening estende ConnectionsTab e só sobrescreve o `_fetch()` —
muda a query do backend (`list_listening` filtra `LISTEN` ou peer
`*` para UDP). Resto do código (UI, filtro, auto-refresh, admin mode)
herda.

Auto-refresh usa `GLib.timeout_add_seconds(3, ...)`. Quando o widget
fica `unmap` (usuário trocou de ferramenta no Hub) o timeout é removido
para não gastar CPU/subprocess em background. `map` reativa.

Fetch sempre em thread (`threading.Thread(daemon=True)`) + `GLib.idle_add`
no fim. Guard `_fetch_running` evita acumular calls concorrentes de
`ss` quando o usuário spam-clica "Atualizar".

## Comandos disparados

```bash
# Modo normal (user)
ss -tunap                  # processo só visível para sockets do próprio user

# Modo admin (pkexec)
pkexec ss -tunap           # revela process info de TODOS os sockets (root incluso)
```

Format do output do `ss`:

```
Netid State   Recv-Q Send-Q Local Address:Port    Peer Address:Port    Process
udp   UNCONN  0      0      127.0.0.54:53         0.0.0.0:*            users:(("systemd-resolve",pid=804,...))
tcp   ESTAB   0      0      192.168.1.5:43210     142.250.78.46:443    users:(("firefox",pid=12345,...))
tcp   LISTEN  0      128    0.0.0.0:22            0.0.0.0:*            users:(("sshd",pid=900,...))
```

## Tabs / Funcionalidades

### Conexões

Lista todas conexões (TCP+UDP, qualquer estado). Ordem:
`ESTAB` primeiro, depois `LISTEN`, depois resto.

Toolbar:

- **SearchEntry**: filtra por processo, IP, porta (case-insensitive,
  busca em `process|pid|local_addr|peer_addr|proto|state`)
- **Auto switch**: liga/desliga auto-refresh 3s
- **Atualizar btn**: força refresh agora
- **Modo admin (card)**: switch opt-in para rodar via `pkexec`. Quando
  ligado, desabilita auto-refresh (não spammar polkit em background) e
  só atualiza ao clicar "Atualizar"

Cores no badge de estado:

| Estado | CSS class |
|---|---|
| `ESTAB` | `success` (verde) |
| `LISTEN` | `accent` |
| `TIME-WAIT` / `UNCONN` | `dim-label` |
| `CLOSE-WAIT` / `SYN-SENT` / `SYN-RECV` | `warning` (âmbar) |

### Listening

Subclasse de Connections que filtra para mostrar só servidores ativos
no host (estado `LISTEN` ou UDP com peer `*`). Crítico para responder
"o que está exposto na rede agora?".

## Quando usar

- Auditar exposição de rede antes de plugar laptop em rede pública
  (aba Listening: tudo o que aparecer está aceitando conexões)
- Investigar conexão suspeita: filtra por IP estranho na busca,
  vê qual processo está conversando
- Confirmar que um serviço local subiu na porta esperada
- Detectar processos zumbi em `CLOSE-WAIT` (anomalia se persistir muito
  tempo — peer fechou mas seu app não)

## Limitações conhecidas

- Sem DNS reverso — IPs aparecem numéricos (v0.2)
- Sem bandwidth por processo — para isso é `nethogs`
- Auto-refresh roda `ss` sync — em hosts com 1000+ conexões pode ter
  latência perceptível (raro em desktop)
- Modo admin pede senha a cada refresh manual — não há cache de polkit
- Parser de `ss` é regex sobre output legível para humanos — formatos
  novos do `iproute2` podem quebrar (test suite cobre os comuns)

## Trecho de código relevante

```python
# backend.py — parser de ss -tunap
def _parse_ss_output(output: str) -> list[NetConnection]:
    conns: list[NetConnection] = []
    process_re = re.compile(r'\("([^"]+)",pid=(\d+)')

    for line in output.splitlines():
        line = line.rstrip()
        if not line or line.startswith("Netid"):
            continue
        # Limita splits para preservar process info (que tem virgulas/parens)
        parts = line.split(None, 6)
        if len(parts) < 6:
            continue
        netid, state, _recv, _send, local, peer = parts[:6]
        process_info = parts[6] if len(parts) > 6 else ""

        m = process_re.search(process_info)
        if m:
            process_name, pid = m.group(1), m.group(2)
        else:
            process_name, pid = "?", "?"

        conns.append(NetConnection(
            proto=netid, state=state,
            local_addr=local, peer_addr=peer,
            process=process_name, pid=pid,
            raw=line,
        ))
    return conns
```

```python
# connections.py — pausa auto-refresh quando o user troca de tool no Hub
def _on_widget_map(self, _widget) -> None:
    """Widget acabou de ficar visivel (tool selecionada no Hub)."""
    if self._auto_switch.get_active() and not self._elevated_mode:
        self._start_auto_refresh()

def _on_widget_unmap(self, _widget) -> None:
    """Widget ficou invisivel (user trocou de tool). Para o auto-refresh
    pra nao gastar CPU/subprocess em background."""
    self._stop_auto_refresh()
```

```python
# connections.py — modo admin não força refresh para evitar spam de polkit
def _on_elevated_toggle(self, switch: Gtk.Switch, value: bool) -> bool:
    """Toggle modo admin (pkexec). Importante: NAO forca refresh imediato.
    Se um misclick liga/desliga o switch varias vezes, sem o force-refresh
    nao acumula dialogs de polkit."""
    self._elevated_mode = value
    if value:
        if self._auto_switch.get_active():
            self._auto_switch.set_active(False)
        self._auto_switch.set_sensitive(False)
    else:
        self._auto_switch.set_sensitive(True)
    switch.set_state(value)
    return True
```
