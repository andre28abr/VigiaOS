# Network Monitor (netmon-gui)

## Em uma frase

Wrapper GTK4 do `ss -tunap` (socket statistics) com auto-refresh, redesenhado
(v0.2.0) para responder **"quem usa minha internet"**: aba **Conexões**
agrupada por aplicativo, com DNS reverso, estados em PT-BR e loopback
escondido por padrão; aba **Escutando** com glossário de portas e escopo
(local/exposta).

## O que envolve

| Item | Valor |
|---|---|
| **Pacotes Linux** | `iproute2` (fornece `ss`), `polkit` |
| **Comando principal** | `ss -tunap` (TCP+UDP, no DNS resolve, all states, process info) |
| **Permissões** | Read-only sem auth. Modo admin opt-in via `pkexec ss -tunap` para revelar processos system |
| **Stack** | Python 3.11+ · PyGObject · GTK4 · libadwaita 1 |
| **Path config** | Sem state local — coleta tudo em runtime |
| **App ID** | `br.com.vigia.NetMon` |
| **Versão** | 0.2.0 |

## Arquitetura interna

```
vigia_netmon/
├── backend.py     — list_connections(elevated=False) → list[NetConnection]
├── humanize.py    — estados PT-BR, glossário de portas, loopback/internet, DNS reverso (cache)
├── window.py      — build_content() monta ViewStack das 2 tabs
└── tabs/
    ├── connections.py — "quem usa a internet": agrupado por app, DNS reverso, internas escondidas
    └── listening.py   — subclasse: servidores ativos no host, com glossário de portas
```

A tab **Escutando** (`ListeningTab`) estende `ConnectionsTab` e reusa a
máquina de refresh/admin/filtro — sobrescreve só os **hooks**: `_fetch`
(usa `list_listening`), `_prefilter` (no-op, aqui o conteúdo SÃO os sockets
escutando), `_summary_text` e `_render_into` (layout por porta).

`NetConnection.is_listening` (`state == "LISTEN"` ou `peer_addr` termina em
`:*`) separa as duas abas: **Conexões** filtra esses **fora**; **Escutando**
mostra **só** eles.

Auto-refresh usa `GLib.timeout_add_seconds(3, ...)`. Quando o widget fica
`unmap` (usuário trocou de ferramenta no Hub) o timeout é removido para não
gastar CPU/subprocess em background. `map` reativa.

Fetch sempre em thread (`threading.Thread(daemon=True)`) + `GLib.idle_add`
no fim. Guard `_fetch_running` evita acumular calls concorrentes de `ss`.

## humanize.py (módulo puro, testável)

Toda a "humanização" do output do `ss` mora aqui — funções puras, exceto o
DNS reverso (que toca a rede, só chamado em thread, com cache):

- **`state_label(state)`** — `ss` → PT-BR:
  `ESTAB`→**Conectado**, `LISTEN`→**Escutando**,
  `TIME-WAIT`/`CLOSE-WAIT`/`FIN-WAIT-*`/`LAST-ACK`/`CLOSING`→**Encerrando**,
  `UNCONN`→**Inativo**, `SYN-SENT`/`SYN-RECV`→**Conectando**.
- **`split_host_port(addr)`** — separa host/porta, lidando com IPv6 entre
  colchetes (`[::1]:53`).
- **`is_loopback(addr)`** / **`is_internet_peer(addr)`** — `is_internet_peer`
  é `False` pra loopback **e** pra wildcards de socket (`*`, `0.0.0.0`, `::`).
  É o que decide o filtro "Internas" da aba Conexões.
- **`port_hint(port)`** — glossário `PORT_GLOSSARY` (22→"Acesso remoto (SSH)",
  631→"Impressão (CUPS)", 5353→"Descoberta de rede (mDNS/Bonjour)", 53→"DNS",
  443→"Web seguro (HTTPS)", 5432→"Banco de dados (PostgreSQL)", … ~28 portas).
- **`resolve_host(ip)`** — DNS reverso (PTR) via `socket.gethostbyaddr`, com
  cache em `_DNS_CACHE` e `""` se não resolver. **BLOQUEIA** → só em thread.

## Comandos disparados

```bash
# Modo normal (user)
ss -tunap                  # processo só visível para sockets do próprio user

# Modo admin (pkexec)
pkexec ss -tunap           # revela process info de TODOS os sockets (root incluso)
```

## Tabs / Funcionalidades

### Conexões ("quem usa minha internet")

Agrupada **por aplicativo**. Pipeline de cada refresh:

1. `_fetch()` → `backend.list_connections(elevated)`.
2. `_prefilter()` remove `is_listening` (vão pra aba Escutando) e, se o
   toggle **Internas** está **off** (padrão), mantém só
   `humanize.is_internet_peer(peer_addr)` — esconde loopback.
3. `_render_into()` agrupa por `process` (processos sem nome → grupo
   *"(apps do sistema)"*), uma `Adw.ExpanderRow` por app (expandida se ≤ 4
   conexões). Cada destino vira uma `ActionRow` com `state_label` + porta e
   um badge de estado colorido.
4. `_kick_resolve()` dispara o **DNS reverso async** numa thread; quando
   resolve, `_apply_names` troca o título da row pro hostname e move o IP
   pro subtítulo.

Resumo no topo (`_summary_text`): *"N apps na internet · M conexões"*.

Toolbar: **SearchEntry** (filtra por app/site/porta), **Internas** (Switch,
off=esconde loopback), **Auto** (refresh 3s), **Atualizar**, e o card de
**Modo admin**.

Cores do badge de estado (`STATE_CSS`):

| Estado (`ss`) | Rótulo | CSS class |
|---|---|---|
| `ESTAB` | Conectado | `success` (verde) |
| `LISTEN` | Escutando | `accent` |
| `TIME-WAIT` / `UNCONN` | Encerrando / Inativo | `dim-label` |
| `CLOSE-WAIT` / `SYN-SENT` / `SYN-RECV` | Encerrando / Conectando | `warning` |

### Escutando (`ListeningTab`)

Servidores ativos no host (`LISTEN` ou UDP `UNCONN`), **ordenados por número
de porta**. Cada `ActionRow`:

- **Título**: `Porta <n> — <glossário>` (via `humanize.port_hint`).
- **Subtítulo**: `<app> · <PROTO> · <escopo>`, onde o **escopo** é:
  - `0.0.0.0` / `::` / `*` → **"aberta pra qualquer rede"**
  - loopback → **"só neste PC (local)"**
  - senão → o IP de bind.
- **Selo "exposta"** (`warning` caption) quando o bind é wildcard — sinaliza
  o que aceita conexão de qualquer interface.

Sem toggle "Internas" aqui (`_show_hide_local = False`): tudo é local por
natureza. Crítico pra responder "o que está exposto na rede agora?".

### Modo admin

Switch opt-in (card) que roda via `pkexec`. Quando ligado, desabilita o
auto-refresh (não spammar polkit em background) e só atualiza ao clicar
**Atualizar**. O toggle **não** força refresh imediato — assim um misclick
não acumula diálogos de polkit.

## Quando usar

- **"Quem usa minha internet"**: aba Conexões, agrupada por app, com nomes
  de site (DNS reverso) em vez de IPs crus.
- **Auditar exposição** antes de plugar em rede pública: aba Escutando,
  caçar os selos **"exposta"**.
- **Investigar conexão suspeita**: filtra por nome/IP estranho na busca, vê
  qual app está conversando.
- **Confirmar bind**: serviço local subiu na porta e no escopo esperados.

## Limitações conhecidas

- DNS reverso depende de PTR configurado — muitos IPs de CDN não resolvem e
  permanecem numéricos.
- Sem bandwidth por processo — para isso é o Dashboard (aba Rede, `nethogs`).
- Auto-refresh roda `ss` sync — em hosts com 1000+ conexões pode ter latência
  perceptível (raro em desktop).
- Modo admin pede senha a cada refresh manual — não há cache de polkit.
- Parser de `ss` é regex sobre output legível — formatos novos do `iproute2`
  podem quebrar (test suite cobre os comuns).

## Trecho de código relevante

```python
# connections.py — prefiltro: sockets escutando saem; loopback escondido por padrão
def _prefilter(self, conns):
    conns = [c for c in conns if not c.is_listening]
    if (self._hide_local_switch is not None
            and not self._hide_local_switch.get_active()):
        conns = [c for c in conns if humanize.is_internet_peer(c.peer_addr)]
    return conns
```

```python
# connections.py — DNS reverso async, aplicado por cima da lista já mostrada
def _resolve_worker(self, ips):
    names = {ip: humanize.resolve_host(ip) for ip in ips}
    GLib.idle_add(self._apply_names, names)

def _apply_names(self, names):
    for row, ip, base_sub in self._resolve_rows:
        name = names.get(ip)
        if name:
            row.set_title(name)
            row.set_subtitle(f"{ip} · {base_sub}")
    return False
```

```python
# listening.py — escopo + selo "exposta" por porta
host, port = humanize.split_host_port(c.local_addr)
hint = humanize.port_hint(port)
row.set_title(f"Porta {port}" + (f" — {hint}" if hint else ""))
if host in ("0.0.0.0", "::", "*"):
    scope = "aberta pra qualquer rede"
elif humanize.is_loopback(c.local_addr):
    scope = "só neste PC (local)"
else:
    scope = host
```
