# Vigia Activity Log

> Parseador de logs do Linux com narrativa human-readable.
> Converte ruído de `auditd` / `journald` / `fail2ban` em frases que
> dizem **o que aconteceu**, **quem fez**, **quando** e **por quê é notável**.

## Estado

🟢 **v0.6** — classificador per-evento (`Routine` / `Interesting` / `Suspicious`)
com filtro `s` na TUI e `--min-severity` na CLI. Cada linha ganha indicador
visual ● (vermelho = suspeito, âmbar = interessante, · cinza = rotineiro).

Regras de classificação (resumo):

| Source | Suspicious | Interesting | Routine |
|---|---|---|---|
| audit AVC | permissive=0 | permissive=1 | — |
| audit USER_AUTH | res!=success | — | res=success |
| audit USER_LOGIN | res!=success | — | res=success |
| audit ANOM_* | PROMISCUOUS | ABEND | — |
| audit SYSCALL | — | success!=yes | success=yes |
| journal | EMERG/ALERT/CRIT | ERR/WARNING | NOTICE/INFO/DEBUG |
| fail2ban | Ban | Found | Unban / JailStart / JailStop |

### v0.5 — correlator: detecta padrões cross-source e sintetiza em narrativas únicas.

Salto qualitativo: a ferramenta deixa de ser "lista de eventos" e vira "insight sobre
o que aconteceu". Padrões detectados:

| Pattern | Severidade | O que detecta |
|---|---|---|
| `fail2ban_burst` | SUSP | N×Found mesmo IP → Ban em até 2min (N≥2) |
| `oom_kill` | INFO | journal CRIT OOM, opcionalmente confirmado por audit ANOM_ABEND |
| `selinux_burst` | INFO | 3+ AVC denials mesmo `comm` em até 60s |
| `suspicious_ssh_login` | SUSP | Accepted publickey + ≥1 Found anterior do mesmo IP em 10min |

Painel de correlations aparece automaticamente na TUI quando há detecções
(toggle com `c`).

### v0.4 — três fontes mergeadas cronologicamente: audit + journald + fail2ban.

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
sudo vigia-log -o text                # CLI pipe-friendly (correlations + events)
sudo vigia-log -o json | jq .         # JSON discriminado por source
sudo vigia-log -o correlations        # só as narrativas sintetizadas

# Filtro de severidade (reduz ruído drasticamente)
sudo vigia-log --min-severity interesting   # esconde rotineiros (SYSCALL ok, login ok, INFO, ...)
sudo vigia-log --min-severity suspicious    # só o que merece atenção (AVC denial, Ban, CRIT, ...)

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
| `s` | Cycle min-severity (All → Interesting+ → Suspicious → All) |
| `/` | Entra em modo de busca |
| `c` | Toggle visibilidade do painel de correlations |
| `Esc` | Limpa todos os filtros e busca |
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
- ✅ v0.5: correlator com 4 padrões (fail2ban_burst, oom_kill, selinux_burst, suspicious_ssh_login). Painel toggleavel na TUI. Modo `-o correlations`.
- ✅ v0.6: classificador per-evento (Routine/Interesting/Suspicious). Filtro `s` na TUI + `--min-severity` na CLI. Badge ● visual.
- v0.7: live mode (`-f` tail) — atualiza TUI em tempo real conforme audit/journal crescem
- v0.8: empacotamento — Cargo.io publish + COPR rpm

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
├── correlator.rs # detecta padrões cross-source e gera Correlation com summary + severity
├── narrator.rs   # Event → frase em português (dispatch por variant)
└── tui.rs        # interface Ratatui (App struct, filtros, search)
```

### Decisões

- **Parser hand-rolled** para audit em vez de nom/regex: formato é simples e estável, dependência a menos.
- **journalctl pipe** em vez de libsystemd: sem FFI, portável, fácil de testar com snapshot.
- **Event enum interna** preserva a riqueza de cada source (AuditEvent não vira `HashMap<String, String>`). Narrator dispatcheia.
- **Sem async**: arquivos são lidos inteiros. Tail/follow vai vir em v0.7 com `notify` crate ou polling.
- **Cores hard-coded** em `tui.rs` no padrão VigiaOS. Config quando outras ferramentas aparecerem.
