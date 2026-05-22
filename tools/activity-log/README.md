# Vigia Activity Log

> Parseador de logs do Linux com narrativa human-readable.
> Converte ruído de `auditd` / `journald` / `fail2ban` em frases que
> dizem **o que aconteceu**, **quem fez**, **quando** e **por quê é notável**.

## Estado

🟢 **v0.4** — três fontes mergeadas cronologicamente: audit + journald + fail2ban.

- Sources:
  - `audit` (/var/log/audit/audit.log)
  - `journald` (via `journalctl -o json` ou snapshot JSON)
  - `fail2ban` (/var/log/fail2ban.log)
- Eventos interleavados por timestamp, navegáveis na mesma lista
- Tags `[A]` / `[J]` / `[F]` na TUI distinguem origem
- Narrator em português:
  - Audit: AVC, USER_AUTH, USER_LOGIN, USER_ACCT, ANOM_*, SYSCALL
  - Journal: priority tag ([ERR], [WARN], [CRIT], etc.) + unit/comm
  - Fail2ban: BANIU / liberou / detectou tentativa + IP + jail
- Cores semânticas por severidade (vermelho crítico, âmbar warning, etc.)
- Filtros: cycle por tipo (`f`), search incremental (`/`)
- Modos de saída: TUI (default), texto, JSON discriminado por source

### Sobre firewalld

O `firewalld` **não tem log próprio em arquivo**; ele loga via systemd journal.
Então use `--sources journald` e busque por "firewalld" (com `/`). Drops de
kernel iptables/nftables também caem no journal com `_TRANSPORT=kernel`.

## Build

Precisa de Rust ≥ 1.75 (instalado via `bootstrap.sh` do VigiaOS):

```bash
cd tools/activity-log
cargo build --release
# binário em: target/release/vigia-log
```

Para instalar globalmente após build:
```bash
sudo install -m 0755 target/release/vigia-log /usr/local/bin/vigia-log
```

## Uso

```bash
# Default: só audit.log
sudo vigia-log

# Multi-source — todas as fontes mergeadas cronologicamente
sudo vigia-log --sources audit journald fail2ban

# Só journal
sudo vigia-log --sources journald

# Modos de saída
sudo vigia-log -o text                # CLI pipe-friendly
sudo vigia-log -o json | jq .         # JSON discriminado por source

# Override paths (útil para fixtures e dev)
vigia-log --sources audit journald \
  --audit-path tests/fixtures/sample-audit.log \
  --journal-path tests/fixtures/sample-journal.json

# Stdin via '-'
journalctl -o json --no-pager | vigia-log --sources journald --journal-path -

# Últimos 50 eventos só
vigia-log --limit 50
```

### Capturar snapshot do journal para testar no Mac

Para iterar a TUI no Mac sem `journalctl` disponível, gere um snapshot na VM
e leve para o Mac:

```bash
# Na VM Silverblue:
sudo journalctl -o json --no-pager -n 500 > /tmp/journal-snap.json
scp /tmp/journal-snap.json mac:~/

# No Mac:
vigia-log --sources journald --journal-path ~/journal-snap.json
```

## Atalhos da TUI

**Modo normal:**

| Tecla | Ação |
|---|---|
| `↑` / `k` | Sobe um evento |
| `↓` / `j` | Desce um evento |
| `PageUp` / `PageDown` | Pula 10 |
| `Home` / `End` | Primeiro / último |
| `f` | Cycle filter por tipo (AVC → USER_AUTH → ... → None) |
| `/` | Entra em modo de busca |
| `Esc` | Limpa filtros e busca |
| `q` | Sai |

**Modo busca (após `/`):**

| Tecla | Ação |
|---|---|
| (caracteres) | Adiciona à query — filtra a lista em tempo real |
| `Backspace` | Apaga último caractere |
| `↑↓` | Navega a lista filtrada |
| `Enter` | Confirma busca (volta ao modo normal, mantém filtro) |
| `Esc` | Cancela (limpa busca) |

A query de busca é case-insensitive e aplica em cima da narrativa completa
(timestamp + tipo + texto). Matches são destacados em verde esmeralda na lista.

## Roadmap

- ✅ v0.1: parser + narrator + TUI básico para audit.log
- ✅ v0.2: filtros (por tipo, cycle com `f`); search incremental (`/`); highlight de matches
- ✅ v0.3: source `journald` (via `journalctl -o json`), Event abstraction, merge cronológico, cores por priority syslog
- ✅ v0.4: source `fail2ban` (Ban/Unban/Found + IP + jail). Firewalld coberto via journald.
- v0.5: correlator (junta eventos relacionados de fontes diferentes em "narrativas" únicas)
- v0.6: classificador automático (rotineiro / interessante / suspeito) + filtro `s` para "só suspeito"
- v0.7: live mode (`-f` tail) — atualiza TUI em tempo real conforme audit/journal crescem

## Testes

```bash
cargo test
```

Fixtures em `tests/fixtures/sample-audit.log` cobrem os tipos mais comuns.

## Arquitetura

```
src/
├── main.rs       # CLI (clap) — orquestra sources, output, limit
├── event.rs      # enum Event { Audit, Journal } — abstração unificada
├── audit.rs      # parser + agrupamento de audit.log
├── journal.rs    # parser de journalctl -o json + Priority syslog
├── fail2ban.rs   # parser de /var/log/fail2ban.log + Action enum (Ban/Unban/Found)
├── narrator.rs   # Event → frase em português (dispatch por variant)
└── tui.rs        # interface Ratatui (App struct, filtros, search)
```

### Decisões

- **Parser hand-rolled** para audit em vez de nom/regex: formato é simples e estável, dependência a menos.
- **journalctl pipe** em vez de libsystemd: sem FFI, portável, fácil de testar com snapshot.
- **Event enum interna** preserva a riqueza de cada source (AuditEvent não vira `HashMap<String, String>`). Narrator dispatcheia.
- **Sem async**: arquivos são lidos inteiros. Tail/follow vai vir em v0.7 com `notify` crate ou polling.
- **Cores hard-coded** em `tui.rs` no padrão VigiaOS. Config quando outras ferramentas aparecerem.
