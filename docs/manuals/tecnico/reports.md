# Reports

## Em uma frase

Gerador de relatorios HTML (preparados para impressao em PDF via
navegador) que consolida eventos de autenticacao e atividade do sistema
a partir de `journalctl`, `last` e `lastb` — pensado para auditoria LGPD.

## O que envolve

| Item | Valor |
|---|---|
| **Pacote** | `vigia-reports` (versao 0.1.1) |
| **App ID** | `br.com.vigia.Reports` |
| **Pacotes wrapped** | `journalctl`, `last`, `lastb` |
| **Templating** | Jinja2 (`PackageLoader("vigia_reports", "templates")`) |
| **Render PDF** | Firefox/Chromium (Ctrl+P -> "Salvar como PDF") |
| **Saida** | HTML em `~/.local/share/vigia-reports/` (dir 0700, file 0600) |
| **Privilegios** | `pkexec` opcional (modo admin para journal completo + `lastb`) |
| **Stack** | Python 3.11+ . PyGObject . GTK4 . libadwaita 1 |

> Nota sobre WeasyPrint: o projeto explicitamente **nao** usa
> WeasyPrint/ReportLab para gerar PDF nativamente. A racional esta no
> `tabs/about.py`: o stack (libcairo+pango+gdk-pixbuf) e' problematico em
> Silverblue. O navegador imprime o mesmo HTML com fidelidade identica.

## Arquitetura interna

```
vigia_reports/
|-- backend.py           # coletores (journalctl/last/lastb) + parsers + agregadores
|-- renderer.py          # Jinja2 PackageLoader + write_report (chmod 0600)
|-- window.py            # build_content() — Adw.ToolbarView + ViewStack
|-- app.py / __main__.py # standalone entrypoint
|-- tabs/
|   |-- generate.py      # form: template + periodo + modo admin + Gerar
|   |-- library.py       # lista HTMLs salvos + abrir/excluir
|   `-- about.py
`-- templates/
    |-- base.html
    |-- activity_overview.html
    `-- auth_events.html
```

Fluxo de geracao (executado em `threading.Thread` para nao bloquear UI):

1. `backend.make_period(days)` calcula `since/until`.
2. `collect_for_activity_overview(period, elevated=True)` ou
   `collect_for_auth_events(...)` chama `_gather(period, elevated)`.
3. Se `elevated=True`, `_gather` invoca `collect_all_elevated(period)`
   que consolida **TODOS** os comandos em **um unico** `pkexec bash -c
   '<script>'`, separando secoes por um marcador UUID. Reduz N polkit
   dialogs para 1.
4. Parsers puros (`_parse_ssh_journal`, `_parse_sudo_journal`,
   `_parse_fail2ban_journal`, `_parse_pkexec_journal`, `_parse_last_text`)
   transformam stdout bruto em `list[dict]`.
5. `renderer.render_html(template_id, data)` aplica Jinja2.
6. `renderer.write_report(html, template_id, output_dir)` salva com
   `chmod 0600` (LGPD).

Migracao automatica one-shot: arquivos legados em
`~/Documents/VigiaReports/` sao movidos para
`~/.local/share/vigia-reports/` no primeiro `ensure_reports_dir()` —
`~/Documents/` sincroniza em Dropbox/iCloud/OneDrive por default e
relatorios contem PII.

## Comandos disparados

### Modo nao-elevado (default)

```bash
journalctl --since "<since>" --until "<until>" \
    --output json --no-pager _COMM=sshd
journalctl --since "<since>" --until "<until>" \
    --output json --no-pager _COMM=sudo
journalctl --since "<since>" --until "<until>" \
    --output json --no-pager SYSLOG_IDENTIFIER=fail2ban-server
journalctl --since "<since>" --until "<until>" \
    --output json --no-pager _COMM=pkexec
last -F -n 50
```

### Modo elevado (UM `pkexec`)

```bash
pkexec bash -c '
set +e
journalctl --since "..." --until "..." --output json --no-pager _COMM=sshd
printf "\n===VIGIA-<uuid>===\n"
journalctl ... _COMM=sudo
printf "\n===VIGIA-<uuid>===\n"
# ... fail2ban, pkexec, last, lastb
'
```

A consolidacao num unico `pkexec` e' deliberada — multiplos prompts de
senha derretem UX e treinam o usuario a clicar sem ler.

## Tabs / Funcionalidades

| Tab | Descricao |
|---|---|
| **Gerar** | `ComboRow` template (Atividade geral, Eventos de autenticacao) + `ComboRow` periodo (24h, 7d, 30d, 90d) + `SwitchRow` modo admin + botao `Gerar`. Progress bar pulsante. Abre HTML no navegador via `Gio.AppInfo.launch_default_for_uri`. |
| **Biblioteca** | Lista HTMLs ordenados por mtime desc. Cada row tem `Abrir` + `Excluir` (com `Adw.AlertDialog`). Botao "Abrir pasta" lanca file manager. |
| **Sobre** | `Adw.PreferencesPage` com 5 secoes markup-formatted. |

### KPIs do template `activity_overview`

`ssh_success`, `ssh_failed`, `sudo_invocations`, `pkexec_invocations`,
`bans`, `logins` + top 10 IPs banidos + top 10 usuarios sudo.

### Conteudo do template `auth_events`

`ssh_success`, `ssh_failed`, `sudo` completo, `pkexec` completo,
`logins` (last) e `failed_logins` (lastb — so com modo admin).

## Quando usar

- **Revisao mensal de atividade**: `activity_overview` ultimos 30 dias,
  salvar PDF como evidencia.
- **Auditoria LGPD/conformidade**: `auth_events` ultimos 90 dias mostra
  controle de acesso.
- **Resposta a incidente**: ultimas 24h para isolar atividade suspeita.
- **Mostrar diligencia** para auditor externo.

## Limitacoes conhecidas

- Apenas 2 templates na v0.1.
- Sem agendamento automatico (sem systemd timer).
- Templates fixos — personalizacao requer editar `templates/*.html`.
- `lastb` so com modo admin; sem ele `failed_logins` fica vazio.

## Trecho de codigo relevante

Consolidacao em um unico `pkexec` (`backend.py:308`):

```python
def collect_all_elevated(period: Period) -> dict[str, list[dict]] | None:
    sep = f"===VIGIA-{uuid.uuid4().hex}==="
    script = f"""set +e
journalctl ... _COMM=sshd
printf '\\n{sep}\\n'
journalctl ... _COMM=sudo
# ... 4 outros comandos
"""
    result = subprocess.run(
        ["pkexec", "bash", "-c", script],
        capture_output=True, text=True, timeout=180,
    )
    if result.returncode in (126, 127):
        return None  # usuario cancelou polkit
    sections = result.stdout.split(sep)
    return {
        "ssh": _parse_ssh_journal(_parse_json_lines(sections[0])),
        # ...
    }
```

Hardening LGPD (`renderer.py:78`):

```python
def write_report(html, template_id, output_dir) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir.chmod(0o700)
    path = output_dir / f"{template_id}-{stamp}.html"
    path.write_text(html, encoding="utf-8")
    path.chmod(0o600)
    return path
```
