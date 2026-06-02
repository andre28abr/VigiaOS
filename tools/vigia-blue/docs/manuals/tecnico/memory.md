# Vigia Memory — manual técnico

Módulo de **Forense** do **VigiaBlue**. Wrapper do **Volatility 3**: roda um
plugin sobre um **dump de memória** e parseia a saída JSON numa tabela.

> O Vigia Memory **analisa** um dump existente — **não captura** a RAM (captura
> exige root + AVML/LiME). É o legista, não a coleta.

## Arquivos

```
tools/vigia-blue/src/vigia_blue/modules/memory/
├── __init__.py
├── backend.py     # catálogo + cmd builder + parser JSON (PURO) + run_plugin (IO)
└── page.py        # GUI: Análise / Sobre

tests/blue/test_memory_backend.py   # 11 testes
tools/vigia-blue/docs/manuals/{leigo,tecnico}/memory.md
```

## Dependência

- **Volatility 3** (`vol`, `vol.py` ou `volatility3` no PATH). `vol_binary()`
  procura os três; `vol_available()` = achou algum. Sem ele, a GUI mostra banner
  + instrução (`pipx install volatility3`).

## Backend (`backend.py`)

Puro/testável (sem volatility, sem gi):
- **`PLUGINS` / `plugins()`** — catálogo de 11 plugins (Linux + Windows) com
  `id` (caminho real, ex.: `linux.pslist.PsList`), `label`, `os` e `description`
  leiga.
- **`build_vol_cmd(dump, plugin, vol_bin=None)`** — `[bin, "-f", dump, "-r",
  "json", plugin]` (lista, nunca shell string).
- **`parse_vol_json(text) -> (colunas, linhas)`** — a saída `-r json` é um array
  de objetos; colunas = união das chaves na ordem de aparição, descartando
  internas (`__children`). Nunca crasha (JSON inválido / não-lista → `([], [])`).
- **`row_summary(cols, row, n=2)`** — título curto de uma linha (1ªs n colunas
  não vazias) — usado no `ExpanderRow`.

Toca o sistema:
- **`run_plugin(dump, plugin, timeout=600, max_rows=1000)`** — checa binário +
  existência do dump, roda via `proc.run`, parseia, limita linhas, guarda
  `raw_tail` p/ debug. Nunca levanta.

## GUI (`page.py`)

`build_content()` → `ToolbarView` + `ViewSwitcher` (Análise / Sobre).
- **Análise** (`_AnalyzeView`): seletor de dump (`Gtk.FileDialog`), **plugin**
  num `Adw.ComboRow` (rótulo + `(os)`; descrição vai pro subtítulo ao mudar),
  botão **Analisar**, banner se faltar Volatility. Roda em `threading.Thread` →
  `idle_add`. Resultado = **`ExpanderRow` por linha** (título = `row_summary`;
  expandido = cada coluna→valor). Mostra até 400 linhas (cap de UI).

## Privilégio / LGPD

- Roda **sem root** (analisa um arquivo do usuário). A captura do dump (fora do
  escopo) é que exige privilégio.
- 100% local. (Dumps de memória podem conter dados pessoais → tratar o arquivo
  com cuidado é responsabilidade do operador.)

## Pendências (próximos passos)

1. **Histórico** de análises (0600), como nos demais módulos.
2. Render em **tabela real** (`Gtk.ColumnView`) com ordenação por coluna.
3. Detecção automática do perfil/OS do dump; symbol tables (ISF) p/ Linux.
4. Capturar dump local (opt-in, via AVML, com pkexec).
