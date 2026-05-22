# Vigia Activity Log

> Parseador de logs do Linux com narrativa human-readable.
> Converte ruído de `auditd` / `journald` / `fail2ban` em frases que
> dizem **o que aconteceu**, **quem fez**, **quando** e **por quê é notável**.

## Estado

🟢 **MVP em Rust + Ratatui**, primeira fonte: `audit.log`.

- Parser de linhas (`type=X msg=audit(epoch:id): k=v ...`)
- Agrupamento de records por audit_id em "eventos"
- Narrator em português para os tipos mais comuns (AVC, USER_AUTH, USER_LOGIN, USER_ACCT, ANOM_*, SYSCALL)
- TUI navegável com paleta VigiaOS (zinc + emerald)
- Modos de saída: TUI (default), texto, JSON

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
# TUI interativa (default; precisa sudo pois audit.log é restrito)
sudo vigia-log

# Modo texto narrativo (CLI pipe-friendly)
sudo vigia-log -o text

# JSON estruturado (uma linha por evento) — bom para grep/jq
sudo vigia-log -o json | jq .

# De um arquivo específico ou stdin
vigia-log --path tests/fixtures/sample-audit.log
journalctl -u auditd -o cat | vigia-log --path -

# Últimos 50 eventos só
vigia-log --limit 50
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
- v0.3: adicionar source `journald` (systemd journal)
- v0.4: adicionar source `fail2ban`
- v0.5: correlator (junta eventos relacionados em "narrativas")
- v0.6: classificador (rotineiro / interessante / suspeito) + cores

## Testes

```bash
cargo test
```

Fixtures em `tests/fixtures/sample-audit.log` cobrem os tipos mais comuns.

## Arquitetura

```
src/
├── main.rs       # CLI entrypoint (clap)
├── audit.rs      # parser de linhas + agrupamento
├── narrator.rs   # event → frase em português
└── tui.rs        # interface Ratatui
```

### Decisões

- **Parser hand-rolled** em vez de nom/regex: formato é simples e estável, dependência a menos.
- **Sem async**: arquivo é lido inteiro; tail/follow vai depois (turn ainda não decidido entre `notify` crate ou polling).
- **Cores hard-coded** em `tui.rs` no padrão VigiaOS. Vai virar config quando outras ferramentas aparecerem.
- **`field()` retorna o primeiro match em qualquer record do evento**: simplifica narrator, mas pode mascarar conflitos (improvável na prática).
