# Vigia Memory — manual técnico

Módulo de **Forense** do **VigiaBlue**. Wrapper do **Volatility 3**: roda um
plugin sobre um **dump de memória** e parseia a saída JSON numa tabela.

> O Vigia Memory **analisa** um dump existente **e** captura a RAM desta máquina
> (botão Capturar → AVML via pkexec). É o legista — e agora também faz a coleta.

## Arquivos

```
tools/vigia-blue/src/vigia_blue/modules/memory/
├── __init__.py
├── backend.py     # catálogo + cmd + parser (PURO) + run_plugin + captura (IO)
└── page.py        # GUI: Análise (+ Capturar) / Sobre

install/_mem_capture.sh              # helper privilegiado (pkexec): AVML + chown
tests/blue/test_memory_backend.py   # 17 testes
tools/vigia-blue/docs/manuals/{leigo,tecnico}/memory.md
```

## Dependências

- **Volatility 3** (`vol`, `vol.py` ou `volatility3` no PATH) — a **análise**.
  `vol_binary()` procura os três; sem ele a GUI mostra banner + instrução.
- **AVML** (`avml`) — a **captura** (opcional). `avml_path()` procura no PATH e
  em `~/.local/bin` / `/usr/local/bin`. Sem ele, o botão Capturar fica desligado.
  `./install/blue-deps.sh` baixa o binário oficial da Microsoft.

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

### Captura (`capture_dump`, opcional — exige root)

- **`avml_path()` / `avml_available()`** — acha o AVML (PATH + locais comuns).
- **`default_dump_path()`** — `~/teste/memory/captura-<timestamp>.lime`.
- **`build_capture_cmd(out, avml, owner=None)`** — `["pkexec", _mem_capture.sh,
  avml, out, owner]` (lista; nunca shell string).
- **`capture_dump(timeout=900) -> CaptureResult`** — roda o helper privilegiado
  (`install/_mem_capture.sh`) via pkexec: o AVML lê a memória física, grava em
  formato LiME e o helper devolve a posse ao usuário com **0600** (dump = dados
  sensíveis). Nunca levanta; trata pkexec cancelado (rc 126/127).

## GUI (`page.py`)

`build_content()` → `ToolbarView` + `ViewSwitcher` (Análise / Sobre).
- **Análise** (`_AnalyzeView`): seletor de dump (`Gtk.FileDialog`), **botão
  Capturar** (captura a RAM via `capture_dump` em thread → vira o dump
  selecionado), **plugin** num `Adw.ComboRow` (rótulo + `(os)`), botão
  **Analisar**, banner se faltar Volatility. Tudo em `threading.Thread` →
  `idle_add`. Resultado = **`ExpanderRow` por linha** (título = `row_summary`;
  expandido = cada coluna→valor). Mostra até 400 linhas (cap de UI).

## Privilégio / LGPD

- A **análise** roda **sem root** (lê um arquivo do usuário). A **captura** usa
  **pkexec** (UM diálogo polkit) — argv-list, nunca shell string.
- 100% local. O dump capturado fica **0600** em `~/teste/memory/` (dumps podem
  conter senhas/chaves → minimum surface, LGPD).

## Pendências (próximos passos)

1. **Histórico** de análises (0600), como nos demais módulos.
2. Render em **tabela real** (`Gtk.ColumnView`) com ordenação por coluna.
3. **Símbolos (ISF) automáticos p/ Linux** — gerar/baixar o symbol pack do kernel
   do dump (hoje, sem símbolos, a análise de dump Linux falha). Próximo passo p/
   fechar o ciclo capturar→analisar no Linux.
4. ~~Capturar dump local (AVML + pkexec)~~ — **feito** (botão Capturar).
