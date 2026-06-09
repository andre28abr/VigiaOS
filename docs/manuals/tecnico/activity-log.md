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

2. **Frontend Python (`vigia-log-gui`)** em `tools/activity-log-gui/src/vigia_log_gui/` — chama o binário via `subprocess.run`, parseia JSON em dataclasses (`ActivityBundle`, `ActivityEvent`, `ActivityCorrelation`) e renderiza nas 5 tabs.

O frontend é **dumb** quanto ao parsing/classificação: não parseia logs nem classifica severidade — isso fica no Rust, mantendo performance em logs grandes (centenas de MB de audit.log). A **humanização** (rótulos PT-BR + explicações amigáveis), porém, é responsabilidade do frontend, no módulo puro `glossary.py`.

### Camada de humanização (`glossary.py`, v0.2.0)

Módulo **puro** (sem GTK, testável) que traduz o vocabulário técnico:

- **Rótulos de severidade** — `SEVERITY_LABEL`: `suspicious`→**Atenção**,
  `interesting`→**Vale olhar**, `routine`→**Rotina** (antes eram
  SUSP/INFO/OK). `SEVERITY_CSS` mapeia pra `error`/`warning`/`dim-label`.
- **Rótulos de fonte** — `SOURCE_LABEL`: `audit`→**Auditoria de segurança**,
  `journal`/`journald`→**Diário do sistema**, `fail2ban`→**Bloqueios de IP**.
- **`explain(source, narrative, payload)`** — devolve uma `Explanation`
  (`title`, `what`, `normal`, `action`) escolhida por **palavra-chave na
  narrativa** (regras ordenadas: 1ª que casa vence), com fallback por fonte e,
  por fim, um genérico. Cobre login falho, IP bloqueado, comando de admin,
  USB, OOM kill, AVC do SELinux, serviço up/down, boot/shutdown.
- **`SOURCES_INFO`** — `list[SourceInfo]` (code/label/icon/what/when) que
  alimenta a aba **Fontes**.

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
- **Atenção** (vermelho), **Vale olhar** (amarelo), **Rotina** (dim) — via `glossary.severity_label`
- Correlations detectadas
- Timestamp de geração
- Lista de sources disponíveis (detectadas via `detect_available_sources()`)

### Linha do tempo (timeline)

Lista filtrável/buscável de eventos interleavados das fontes. Cada linha é um
`Adw.ExpanderRow` mostrando `[hh:mm:ss] [fonte] narrativa`, com fonte/severidade
já em PT-BR (`source_label`/`severity_label`) e cor por severidade.

**Ao expandir**, o frontend mostra primeiro a explicação amigável de
`glossary.explain(source, narrative, payload)` — três campos (**O que é** /
**É normal?** / **O que fazer**). O **JSON cru** do evento fica atrás de um
sub-expander **"Ver detalhes técnicos"** (`Gtk.Expander`), pra quem quiser o
registro bruto.

Filtros: fonte, severidade mínima (`Vale olhar+`, etc.), search por texto. A
aba expõe `select_source(code)`, chamado pela aba **Fontes** pra focar numa
única fonte.

### Fontes

Novidade da v0.2.0 (`tabs/sources.py`). Um cartão (`Adw.ExpanderRow`) por log
padrão do Fedora, vindo de `glossary.SOURCES_INFO` — **Diário do sistema**,
**Auditoria de segurança**, **Bloqueios de IP** — com o que é, **quando olhar
ali** e um botão **"Ver só este na Timeline"** (`on_focus(code)` → o controller
troca pra aba Linha do tempo e filtra por essa fonte). Fontes ausentes
(`detect_available_sources()`) ganham o selo "indisponível neste PC".

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
