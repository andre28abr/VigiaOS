# Vigia YARA — manual técnico

Módulo de **caça a ameaças** (hunting) do **VigiaBlue**. Wrapper do CLI `yara`,
seguindo o mesmo padrão dos scanners do VigiaHub (Antivírus/Rootkit Scanner):
*escanear path → parsear saída → lista de achados → relatório JSON (0600) +
histórico*.

> **Estado atual (2026-06-01):** backend + GUI prontos. **1º módulo "pronto"
> do ecossistema.** Abas Scan/Histórico/Sobre (`page.py`) ligadas ao shell via
> `Module.impl` — o shell carrega `build_content()` em vez da página "Em breve".
> Essa ponte (`impl`) é o **mecanismo padrão** que todo módulo futuro usa.

## Arquivos

```
tools/vigia-blue/
├── src/vigia_blue/modules/
│   ├── __init__.py
│   └── yara/
│       ├── __init__.py         # mínimo (sem gi — mantém backend testável)
│       ├── backend.py          # wrapper + parser + relatórios (PURO/testável)
│       └── page.py             # GUI: build_content() → abas Scan/Histórico/Sobre
└── data/yara-rules/
    └── starter.yar             # regras de partida (EICAR + webshell + revshell)

tests/blue/test_yara_backend.py # 22 testes (parser, cmd, regras, scan, report)
```

## Dependência

- `yara` (pacote `yara` no Fedora). `yara_available()` = `shutil.which("yara")`.
  Sem ele instalado, o backend não quebra — o scan retorna erro tratado.

## Backend (`backend.py`)

Partes **puras** (testadas sem `yara` nem gi):

- **`parse_yara_output(text) -> list[Match]`** — parser da saída do `yara`.
  Formato: `RuleName /caminho` (1 linha por match) ou `RuleName [tags] /caminho`
  (com `-g`). Ignora: linhas vazias, de `error`/`warning`/`yara:`, e as de
  strings casadas (`-s`, que começam com offset hex `0x...` ou indentadas).
  `Match(rule, path, tags)`.
- **`build_scan_cmd(rules, target, recursive=True) -> list[str]`** — monta o
  argv: `yara -w [-r] REGRA... -- ALVO`. **Lista, nunca shell string** (convenção
  de segurança). O `--` separa opções do alvo (anti flag-injection). `-w`
  silencia warnings de regra (reduz ruído no parse).
- **Descoberta de regras**: `list_rules(dir)` (*.yar/*.yara ordenados),
  `bundled_rules()` (as empacotadas em `data/yara-rules/`), `effective_rules()`
  (regras do usuário em `RULES_DIR` se houver; senão as empacotadas).

Parte que toca o sistema:

- **`scan(target, rules=None, recursive=True, timeout=900) -> ScanResult`** —
  roda via `vigia_common.proc.run` (nunca levanta). `yara` sai `0` mesmo COM
  matches; `rc != 0` **sem stdout** = erro real (regra inválida, path
  inacessível). `ScanResult(target, matches, rules_count, elapsed_sec, error,
  started_at)`.

Relatórios (padrão Antivírus, via `vigia_common.state`):

- **`save_report(result)`** → `~/.local/share/vigia-yara/scan-<ts>.json`, escrita
  atômica `0600` (LGPD — pode conter paths sensíveis).
- **`list_recent_reports(limit)`** → mais novos primeiro, descarta corrompidos.

## Regras de partida (`data/yara-rules/starter.yar`)

Conjunto mínimo e **seguro** (nenhum malware real):
- `EICAR_Test_File` — arquivo-teste padrão de antivírus (valida o scanner).
- `Suspicious_PHP_Webshell` — heurística de webshell (execução dinâmica +
  ofuscação + entrada do usuário).
- `Linux_Reverse_Shell_OneLiner` — padrões de reverse shell (`/dev/tcp/`, `nc -e`,
  socket+subprocess).

Não é ruleset de produção — é ponto de partida/demo. O usuário sobrepõe com as
suas em `~/.local/share/vigia-yara/rules/`.

## Privilégio / LGPD

- Scan de paths do usuário roda **sem root**. Para paths protegidos (root-only),
  a GUI usará **pkexec** (argv-list, nunca shell) — padrão do projeto. (A definir
  na etapa de GUI.)
- Relatórios `0600`; nada sai da máquina (offline por princípio).

## GUI (`page.py`)

`build_content()` retorna um `Adw.ToolbarView` auto-contido (header com
`Adw.ViewSwitcher` + `Adw.ViewStack`):

- **Scan** (`_ScanView`): seletor de pasta (`Gtk.FileDialog.select_folder`),
  info de regras (+ botão "Pasta de regras"), botão **Escanear** (fora de card),
  banner de estado (yara instalado? via `install_hint`), e a lista de matches.
  O scan roda em `threading.Thread` → `GLib.idle_add` (não trava a UI) e salva o
  relatório ao terminar.
- **Histórico** (`_HistoryView`): `list_recent_reports()` → 1 linha por scan
  (alvo, data, nº de matches), com botão **Atualizar**.
- **Sobre**: descrição + path das regras do usuário.

Ligação: `Module.impl="vigia_blue.modules.yara.page"` no registry. O shell
(`vigia_common.shell._module_page`) importa `impl` e chama `build_content()`;
falha de import cai no placeholder (não derruba o app).

## Pendências (próximos passos)

1. Aba **Regras**: listar/baixar/atualizar conjuntos da comunidade.
2. Scan de **PID/memória** (yara suporta `yara regras PID`).
3. **pkexec** para escanear paths root-only (argv-list).
4. Empacotar `data/yara-rules/` (package-data) p/ instalação não-editable + spec COPR.
