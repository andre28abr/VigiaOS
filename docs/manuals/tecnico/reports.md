# Reports

## Em uma frase

Gerador de relatórios HTML (preparados para impressão em PDF via
navegador) que consolida eventos de autenticação e atividade do sistema
a partir de `journalctl`, `last` e `lastb` — pensado para auditoria LGPD.

## O que envolve

| Item | Valor |
|---|---|
| **Pacote** | `vigia-reports` (versão 0.2.4) |
| **App ID** | `br.com.vigia.Reports` |
| **Pacotes wrapped** | `journalctl`, `last`, `lastb` |
| **Templating** | Jinja2 (`PackageLoader("vigia_reports", "templates")`) |
| **Render PDF** | Firefox/Chromium (Ctrl+P -> "Salvar como PDF") |
| **Saída** | HTML em `~/.local/share/vigia-reports/` (dir 0700, file 0600) |
| **Privilégios** | `pkexec` opcional (modo admin para journal completo + `lastb`) |
| **Stack** | Python 3.11+ . PyGObject . GTK4 . libadwaita 1 |

> Nota sobre WeasyPrint: o projeto explicitamente **não** usa
> WeasyPrint/ReportLab para gerar PDF nativamente. A racional está no
> `tabs/about.py`: o stack (libcairo+pango+gdk-pixbuf) é problemático em
> Silverblue. O navegador imprime o mesmo HTML com fidelidade idêntica.

## Arquitetura interna

```
vigia_reports/
|-- backend.py           # coletores + parsers + agregadores + status/resumo + buckets/dia
|-- charts.py            # geradores de grafico SVG (barras, hbar, rosca) — puro, sem deps
|-- renderer.py          # Jinja2 PackageLoader + globals de grafico + write_report (0600)
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

Fluxo de geração (executado em `threading.Thread` para não bloquear UI):

1. `backend.make_period(days)` calcula `since/until`.
2. `collect_for_activity_overview(period, elevated=True)` ou
   `collect_for_auth_events(...)` chama `_gather(period, elevated)`.
3. Se `elevated=True`, `_gather` invoca `collect_all_elevated(period)`
   que consolida **TODOS** os comandos em **um único** `pkexec bash -c
   '<script>'`, separando seções por um marcador UUID. Reduz N polkit
   dialogs para 1.
4. Parsers puros (`_parse_ssh_journal`, `_parse_sudo_journal`,
   `_parse_fail2ban_journal`, `_parse_pkexec_journal`, `_parse_last_text`)
   transformam stdout bruto em `list[dict]`.
5. `renderer.render_html(template_id, data)` aplica Jinja2.
6. `renderer.write_report(html, template_id, output_dir)` salva com
   `chmod 0600` (LGPD).

Migração automática one-shot: arquivos legados em
`~/Documents/VigiaReports/` são movidos para
`~/.local/share/vigia-reports/` no primeiro `ensure_reports_dir()` —
`~/Documents/` sincroniza em Dropbox/iCloud/OneDrive por default e
relatórios contêm PII.

## Comandos disparados

### Modo não-elevado (default)

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

A consolidação num único `pkexec` é deliberada — múltiplos prompts de
senha derretem UX e treinam o usuário a clicar sem ler.

## Tabs / Funcionalidades

| Tab | Descrição |
|---|---|
| **Gerar** | `ComboRow` modelo (Atividade geral, Eventos de autenticação, Resumo executivo, Acesso administrativo, Conformidade LGPD, Saúde do sistema) + `ComboRow` período (24h, 7d, 30d, 90d) + `SwitchRow` modo admin + botão `Gerar`. Progress bar pulsante. Abre HTML no navegador via `Gio.AppInfo.launch_default_for_uri`. |
| **Biblioteca** | Lista HTMLs ordenados por mtime desc. Cada row tem `Abrir` + `Excluir` (com `Adw.AlertDialog`). Toolbar: "Abrir pasta", **"Pacote de auditoria (.zip)"** (`build_audit_package`) e atualizar. |
| **Sobre** | `Adw.PreferencesPage` com 5 seções markup-formatted. |

### KPIs do template `activity_overview`

`ssh_success`, `ssh_failed`, `sudo_invocations`, `pkexec_invocations`,
`bans`, `logins` + top 10 IPs banidos + top 10 usuários sudo.

### Conteúdo do template `auth_events`

`ssh_success`, `ssh_failed`, `sudo` completo, `pkexec` completo,
`logins` (last) e `failed_logins` (lastb — só com modo admin).

### Camada visual (v0.2)

Ambos os modelos ganham, acima das tabelas:

- **Selo de status** + **resumo executivo** — `backend.build_status(kpis)`
  classifica o período em `ok`/`warn`/`danger` (heurística: `danger` = acesso
  SSH bem-sucedido em meio a ≥50 falhas; `warn` = ≥20 falhas ou algum ban) e
  `backend.build_summary()` gera um parágrafo em pt-BR. Renderizados no
  `base.html` (selo no cabeçalho, caixa de resumo) para todo relatório que os
  forneça.
- **Gráficos SVG** (`charts.py`) registrados como globals do Jinja em
  `renderer._make_env()` — `bar_chart` (falhas por dia, via
  `backend.events_by_day`), `hbar_chart` (top IPs banidos / usuários sudo) e
  `donut` (aceitos × falhados). São **SVG inline gerado em Python**: sem JS,
  sem CDN, sem rede (offline/LGPD) e vetorial no print. Texto de dado do
  usuário passa por `html.escape`; usados no template com `| safe`.

### Modelos extras (v0.2.1)

Dois modelos novos, ambos a partir dos dados já coletados:

- **Resumo executivo** (`executive_summary.html` /
  `collect_for_executive_summary`): reaproveita o `activity_overview` e
  acrescenta `build_highlights(kpis)` (bullets concretos). Template compacto —
  status + resumo + KPIs + gráficos + destaques, **sem** as tabelas longas de
  evento. Pensado pra 1 página (cliente/auditor).
- **Acesso administrativo** (`admin_access.html` / `collect_for_admin_access`):
  foco em `sudo` + `pkexec` — quem rodou o quê. Agrega `top_admin_users`,
  `admin_by_day` e nº de administradores distintos; selo via
  `build_admin_status` (≥2 admins → *warn*, nota LGPD do menor privilégio) e
  texto via `build_admin_summary`.
- **Conformidade LGPD** (`lgpd_compliance.html` / `collect_for_lgpd_compliance`):
  snapshot de **postura**, não de logs. `compliance.py` (novo) roda 9 checagens
  **user-readable** (`systemctl is-active`, `getenforce`, `gsettings get`,
  `lsblk` — sem pkexec): firewall, disco LUKS, SELinux, SSH, DNS encriptado,
  fail2ban, telemetria, localização, lock screen. Cada uma vira
  `{label, state, value, detail, critical}` (`state` ∈ ok/warn/off/unknown).
  `compliance_score` ignora *unknown*; `compliance_status` → *danger* se item
  **crítico** (firewall/disco) falha. Interpretação em funções puras
  (`_state_*`) testáveis sem subprocess.
- **Saúde do Sistema** (`system_health.html` / `collect_for_system_health`):
  consolida o **último resultado** que cada tool de segurança persistiu —
  **lendo os arquivos direto, sem importar o código delas** (Reports fica
  desacoplado). `system_health.py` lê: Lynis (`/var/log/lynis-report.dat`,
  `hardening_index`), ClamAV (`~/.local/share/vigia-antivirus/scan-*.json`,
  `infected_files`), AIDE (`~/.config/vigia/file-integrity.json`, `last_check`)
  e rootkits (`~/.local/share/vigia-rootkit/scans/*.json`, `infected_count`).
  Cada um vira `{tool, label, state, headline, detail, ran_at}` (`state` ∈
  ok/warn/danger/**missing**). Tool nunca rodada → *missing* (não conta no
  score). Interpretadores puros (`_interpret_*`) testáveis sem I/O.

### Integridade: selo SHA-256 + pacote de auditoria (v0.2.4)

- **Selo no rodapé** (`renderer._doc_seal`): SHA-256 de `json.dumps(ctx,
  sort_keys=True, default=str)` (dados + metadata; inclui `generated_at`, logo
  é único por documento). Injetado como `doc_seal` e exibido no `base.html`.
  Fingerprint **do conteúdo**, visível na página.
- **Sidecar `.sha256`** (`renderer.write_report`): grava
  `<relatório>.html.sha256` no formato `sha256sum` (`<hash>  <nome>`). Como
  `write_text(utf-8)` grava exatamente `html.encode()`, o digest bate com
  `sha256sum <file>` → **verificável independente** (`sha256sum -c`). É a prova
  de adulteração de verdade (o selo do rodapé é o fingerprint visual).
- **Pacote de auditoria** (`renderer.build_audit_package(reports_dir)`): zipa
  todos os `.html` + os `.sha256` + um `MANIFEST.txt` (lista de hashes) + um
  `LEIA-ME.txt` (passo a passo). Saída `auditoria-<ts>.zip` (0600); botão na
  aba **Biblioteca**.

## Quando usar

- **Revisão mensal de atividade**: `activity_overview` últimos 30 dias,
  salvar PDF como evidência.
- **Auditoria LGPD/conformidade**: `auth_events` últimos 90 dias mostra
  controle de acesso.
- **Resposta a incidente**: últimas 24h para isolar atividade suspeita.
- **Mostrar diligência** para auditor externo.

## Limitações conhecidas

- 6 modelos prontos (sem editor visual de modelo na UI).
- Sem agendamento automático (sem systemd timer).
- Templates fixos — personalização requer editar `templates/*.html`.
- `lastb` só com modo admin; sem ele `failed_logins` fica vazio.

## Trecho de código relevante

Consolidação em um único `pkexec` (`backend.py:308`):

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
