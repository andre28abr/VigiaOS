# Vigia Timeline — manual técnico

Módulo de **Forense** do **VigiaBlue**. Wrapper do **plaso** (`log2timeline.py` +
`psort.py`): constrói uma super-timeline a partir de uma fonte e apresenta os
eventos em ordem cronológica.

## Três entradas (da mais leve à mais pesada)

1. **`analyze_psort_file(path)`** — abre um export `json_line` já pronto. **Não
   exige plaso** (só parseia). É o caminho testável e o mais rápido.
2. **`analyze_storage(.plaso)`** — roda `psort.py` sobre um storage existente.
3. **`run_timeline(source)`** — pipeline completo `log2timeline.py` + `psort.py`
   (lento; exige plaso).

## Arquivos

```
tools/vigia-blue/src/vigia_blue/modules/timeline/
├── __init__.py
├── backend.py     # cmd builders + parser json_line (PURO) + 3 análises (IO)
└── page.py        # GUI: Linha do tempo / Sobre

tests/blue/test_timeline_backend.py   # 13 testes
tools/vigia-blue/docs/manuals/{leigo,tecnico}/timeline.md
```

## Dependência

- **plaso**: `log2timeline.py` e `psort.py` no PATH (`pipx install plaso`).
  `plaso_available()` exige os dois; abrir um export json_line não exige nenhum.

## Backend (`backend.py`)

Puro/testável (sem plaso, sem gi):
- **`build_log2timeline_cmd(storage, source)`** — `[bin, "--status_view",
  "none", storage, source]` (lista, nunca shell string).
- **`build_psort_cmd(storage, output, fmt="json_line")`** — `[bin, "-o", fmt,
  "-w", output, storage]`.
- **`_ts_from_micros(v)`** — timestamp do plaso (inteiro, microssegundos desde
  1970) → ISO UTC; `''` se inválido/≤0.
- **`parse_psort_jsonl(text, max_events=5000)`** — 1 JSON por linha; usa
  `datetime` se houver, senão converte `timestamp` (micros); extrai `message`,
  `data_type`, e a fonte (`source_long`/`parser`/`source_short`). Ignora linhas
  inválidas e não-dict. Nunca crasha.

Toca disco/sistema:
- **`_read_capped`** — lê só os primeiros N bytes (timelines crescem muito).
- `analyze_psort_file` / `analyze_storage` / `run_timeline` — todas devolvem
  `TimelineResult(events, source, total, elapsed_sec, error, started_at)` e
  nunca levantam. Usam `proc.run` (argv em lista) e `tempfile.mkdtemp`.

## GUI (`page.py`)

`build_content()` → `ToolbarView` + `ViewSwitcher` (Linha do tempo / Sobre).
- **Linha do tempo** (`_TimelineView`): três linhas de fonte — **Abrir** export
  json_line (sempre habilitado), **Analisar .plaso** (habilita se `psort_bin`),
  **Gerar de uma pasta** (habilita se `plaso_available`). Tudo em
  `threading.Thread` → `idle_add`. Banner se faltar plaso (lembrando que abrir
  export ainda funciona). Evento = `ActionRow` (data/hora no título, descrição no
  subtítulo, `data_type` como pílula). Mostra até 600 eventos (cap de UI).

## Privilégio / LGPD

- Roda **sem root** (analisa arquivos do usuário). Gerar de discos do sistema
  pode exigir privilégio (pendência: pkexec).
- 100% local. (Timelines podem conter dados pessoais → tratar com cuidado.)

## Pendências (próximos passos)

1. **Histórico** + export do resultado (0600).
2. **Filtro por janela de tempo** e por `data_type`; busca textual.
3. Seleção de parsers do log2timeline (hoje roda o conjunto padrão).
4. pkexec para fontes do sistema (imagens, /var).
