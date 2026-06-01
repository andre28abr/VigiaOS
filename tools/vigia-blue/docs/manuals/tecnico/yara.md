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
    ├── starter.yar             # conjunto "Malware": EICAR + webshell + revshell
    ├── lgpd.yar                # conjunto "LGPD": CPF, CNPJ, e-mail, telefone, cartão
    └── secrets.yar             # conjunto "Credenciais": chave privada, AWS, senhas

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
  argv: `yara -w [-r] REGRA... ALVO`. **Lista, nunca shell string** (convenção
  de segurança). **Sem `--`**: o parser do `yara` não o reconhece (tentaria
  abrir `--` como arquivo). `-w` silencia warnings de regra (reduz ruído).
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

## Regras de partida

**`starter.yar` — malware** (seguro, nenhum malware real):
- `EICAR_Test_File` — arquivo-teste padrão de antivírus (valida o scanner).
- `Suspicious_PHP_Webshell` — heurística de webshell (execução dinâmica +
  ofuscação + entrada do usuário).
- `Linux_Reverse_Shell_OneLiner` — padrões de reverse shell (`/dev/tcp/`, `nc -e`,
  socket+subprocess).

**`lgpd.yar` — dados pessoais (LGPD/PII)**, regex sobre o conteúdo:
- `LGPD_CPF` (suspeito), `LGPD_CNPJ` (baixo), `LGPD_Email` (baixo),
  `LGPD_Telefone_BR` (baixo), `LGPD_Cartao_Credito` (alto). Cada uma com
  `description`/`severity` pt-BR → vira alerta amigável na UI.

> **Limite (importante):** o YARA casa sobre os **bytes** do arquivo. Em texto
> puro (`.txt`/`.csv`/`.log`/`.eml`/código) acha o PII bem. Em `.docx`/`.xlsx`
> (ZIP) e muitos `.pdf` o texto está **comprimido** → o YARA NÃO enxerga. A
> extração desses formatos fica para o futuro módulo **Vigia LGPD / Higiene de
> Dados** (VigiaHub), que extrai o texto antes de casar os padrões. Também é
> *match por formato*, não validação (um CPF inválido casa o padrão).

**`secrets.yar` — credenciais & segredos:**
- `Secret_Private_Key` (alto) — chaves SSH/TLS/PGP em texto; `Secret_AWS_Access_Key`
  (alto) — `AKIA…`; `Secret_Generic_Password` (suspeito) — `password=/secret=/token=`.

**Conjuntos selecionáveis** (`rulesets() -> list[Ruleset]`): cada arquivo `.yar` é
um conjunto (rótulo amigável em `RULESET_INFO` por *stem*), mais o "Tudo".
`effective_rules()` é a **união** de empacotadas + usuário (estas vencem por nome
de arquivo) — base do "Tudo". A GUI (`ComboRow`) passa `ruleset.files` pro
`scan(rules=…)`; sem seleção, o scan usa `effective_rules()`.

Não é ruleset de produção — é ponto de partida. O usuário estende em
`~/.local/share/vigia-yara/rules/`. `count_rules()` conta as declarações `rule X`
(a UI mostra "N regras", não nº de arquivos).

## Privilégio / LGPD

- Scan de paths do usuário roda **sem root**. Para paths protegidos (root-only),
  a GUI usará **pkexec** (argv-list, nunca shell) — padrão do projeto. (A definir
  na etapa de GUI.)
- Relatórios `0600`; nada sai da máquina (offline por princípio).

## GUI (`page.py`)

`build_content()` retorna um `Adw.ToolbarView` auto-contido (header com
`Adw.ViewSwitcher` + `Adw.ViewStack`):

- **Scan** (`_ScanView`): seletor de pasta (`Gtk.FileDialog.select_folder`),
  **seletor de conjunto** (`Adw.ComboRow` populado por `backend.rulesets()`:
  Tudo / Malware / LGPD / Credenciais / conjuntos do usuário) + botão "Pasta de
  regras", botão **Escanear** (fora de card),
  banner de estado (yara instalado? via `install_hint`). O scan roda em
  `threading.Thread` → `GLib.idle_add` (não trava a UI) e salva o relatório.
  **Cada alerta é um `Adw.ExpanderRow`** (clicável): recolhido mostra nome do
  arquivo + severidade colorida; expandido mostra **O que é** (description),
  **Arquivo** (caminho) e **Regra (técnico)** (rule + tags). No fim, um expander
  **"Saída do yara"** (recolhido) com o stdout cru. Resumo no topo do grupo
  (`N alerta(s) em M arquivo(s) · regras · tempo`).
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
