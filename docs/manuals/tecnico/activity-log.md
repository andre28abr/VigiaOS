# Activity Log

## Em uma frase

Frontend GTK4 que consome o JSON bundle do parser Rust `vigia-log`, consolidando `audit.log` + `journald` + `fail2ban.log` numa linha do tempo com narrativa em português e detecção de correlações cross-source.

## O que envolve

| Item | Valor |
|---|---|
| **Pacotes Linux** | `audit` (auditd), `fail2ban` (opcional), `systemd-journald` (sempre presente) |
| **Comando principal** | `vigia-log --output json-bundle --sources <s>` (binário Rust) |
| **Permissões** | user para journald do user; **pkexec** para audit.log e journald do sistema |
| **Stack** | Rust 1.75+ (binário `vigia-log`) + Python 3.11 / PyGObject / GTK4 (`vigia-log-gui`) |
| **Path config** | Nenhum config persistido (state em memória) |
| **Path dados** | Lê `/var/log/audit/audit.log`, `/var/log/fail2ban.log`, journald via `journalctl` |
| **App ID** | `br.com.vigia.ActivityLog` |
| **Versão** | GUI 0.1.0 / engine `vigia-activity-log` 0.7.1 |

## Arquitetura interna

Duas camadas separadas:

1. **Engine Rust (`vigia-log`)** em `tools/activity-log/src/` — módulos:
   - `audit.rs` — parser de `/var/log/audit/audit.log` (Linux Audit)
   - `journal.rs` — parser de `journalctl -o json --no-pager`
   - `fail2ban.rs` — parser de `/var/log/fail2ban.log`
   - `event.rs` — enum `Event { Audit, Journal, Fail2ban }` + classificador de `Severity` (Routine/Interesting/Suspicious)
   - `narrator.rs` — converte cada evento em frase pt-BR
   - `correlator.rs` — detecta 4 padrões cross-source
   - `main.rs` — CLI clap; modo `--output json-bundle` envelopa tudo num JSON com `version`, `generated_at`, `events[]`, `correlations[]`

2. **Frontend Python (`vigia-log-gui`)** em `tools/activity-log-gui/src/vigia_log_gui/` — chama o binário via `subprocess.run`, parseia JSON em dataclasses (`ActivityBundle`, `ActivityEvent`, `ActivityCorrelation`) e renderiza nas 4 tabs.

O frontend é **dumb**: não parseia logs nem classifica severidade. Toda a lógica fica no Rust, mantendo performance em logs grandes (centenas de MB de audit.log).

## Comandos disparados

```bash
# Usuario (sem audit.log)
vigia-log --output json-bundle --limit 500 --sources journald

# Modo admin (switch Admin no header) — 1 dialog polkit por refresh
pkexec vigia-log --output json-bundle --limit 500 \
       --sources audit journald fail2ban
```

`limit=500` aplica por source, então com 3 sources ativos podem vir até 1500 eventos por refresh. A timeline é ordenada cronologicamente após interleavar todas as fontes (`events.sort_by_key(Event::timestamp)`).

Correlations são geradas pós-merge em `correlator::correlate(&events)` e o JSON bundle inclui o array `correlations[]` já resolvido.

## Tabs / Funcionalidades

### Status

Hero card mostrando estado da última coleta + KPI rows:
- Eventos totais
- Suspicious (vermelho), Interesting (amarelo), Routine (dim)
- Correlations detectadas
- Timestamp de geração
- Lista de sources disponíveis (detectadas via `detect_available_sources()`)

### Timeline

Lista filtrável/buscável de eventos interleavados das 3 fontes. Cada linha mostra `[hh:mm:ss] [source] narrativa`. Cores por severidade. Filtros: source (audit/journal/fail2ban), severidade mínima, search por texto.

### Correlations

Lista das 4 narrativas sintetizadas pelo correlator Rust:

- **`fail2ban_burst`** — `N x Found` + `Ban` para mesmo IP em até 120s (`Suspicious`). Exige `Found.len() >= 2`.
- **`oom_kill`** — journald CRIT `Out of memory: Killed X`, pareado com `ANOM_ABEND` do audit dentro de 30s.
- **`selinux_burst`** — 3+ AVC denials para mesmo `comm` em 60s. Sintoma de policy quebrada.
- **`ssh_suspeito`** — journald `Accepted publickey for X from IP` com `Found` prévio do mesmo IP em até 10min.

### Sobre

Versão do GUI + versão do binário `vigia-log` + paths das fontes detectadas + nota sobre o JSON bundle.

### Header

- Switch `Admin` — toggle entre `vigia-log` (sem privilégio) e `pkexec vigia-log` (acesso a audit.log + journald do sistema)
- Botão `Atualizar` (suggested-action) — dispara `threading.Thread` que chama `backend.run_bundle()` e devolve via `GLib.idle_add`
- `ProgressBar` (modo `osd`) pulsando enquanto o Rust trabalha

## Quando usar

- Você viu uma notificação estranha no sistema e quer entender o que aconteceu nos últimos minutos sem decorar `ausearch -i -ts recent` ou `journalctl --since '-10min'`
- Você desconfia de tentativa de brute-force SSH e quer ver as correlations geradas pelo fail2ban
- Você precisa de prova LGPD/auditoria de quem acessou o que e quando
- Você precisa caçar **policy SELinux quebrada** (burst de AVC denials)

## Limitações conhecidas

- Sem `vigia-log` no PATH, a tool mostra erro com instruções pra `cargo build --release` + `sudo install -m 0755 target/release/vigia-log /usr/local/bin/`
- Sem audit instalado (`/var/log/audit/audit.log` não existe), a source `audit` é silenciosamente pulada com warning no stderr
- Modo admin pede senha **a cada refresh** (1 dialog polkit por click no Atualizar). Não há persistência de auth.
- Sem follow/live tail no GUI — pra `tail -f` use o CLI direto: `vigia-log -f --output tui`

## Trecho de código relevante

JSON bundle gerado pelo Rust (formato consumido pelo Python):

```rust
// tools/activity-log/src/main.rs
fn print_json_bundle(events: &[Event], correlations: &[Correlation], sources: &[Source]) {
    let bundle = Bundle {
        version: 1,
        generated_at: chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string(),
        sources: sources_str,
        events_count: events_wire.len(),
        correlations_count: correlations_wire.len(),
        events: events_wire,
        correlations: correlations_wire,
    };
    serde_json::to_writer(out, &bundle)?;
}
```

Frontend Python invocando o binário:

```python
# tools/activity-log-gui/src/vigia_log_gui/backend.py
cmd: list[str] = []
if elevated:
    cmd.append("pkexec")
cmd.append("vigia-log")
cmd += ["--output", "json-bundle"]
cmd += ["--limit", str(limit)]
cmd += ["--sources"] + list(sources)
result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
```
