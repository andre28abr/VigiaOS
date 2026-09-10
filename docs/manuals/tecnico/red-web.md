# Vigia Web Scanner — manual técnico

Módulo de **Aplicações Web** do **VigiaRed**. Wrapper do CLI `wapiti`: rastreia
uma aplicação web autorizada e testa falhas estilo **OWASP** (XSS, SQLi, inclusão
de arquivo, etc.) no nível da aplicação. Saída em **JSON** (`-f json -o arquivo`),
parseada com a stdlib.

> **Pacote:** vigia-red 0.6.2 · **Status:** `pronto`. Padrão do ecossistema:
> *backend puro/testável + `page.py` via `Module.impl`*, atrás do portão de termo
> (`gate.build_gated`). Runner cancelável `vigia_red.runner.ScanProcess`.

## Arquivos

```
tools/vigia-red/src/vigia_red/modules/web/
├── __init__.py     # mínimo (sem gi)
├── backend.py      # perfis + validação + cmd + parser JSON + relatórios (PURO)
└── page.py         # GUI: build_content() → abas Varredura/Histórico/Sobre

tests/red/test_web_backend.py   # 13 testes
```

## Dependência

- **`wapiti`** (wapiti3). `wapiti_available()` = `shutil.which("wapiti")`.
  Instalação (registry `Dependency`, gerenciador `pip`): `pipx install wapiti3`.

## Backend (`backend.py`)

Partes **puras** (testadas sem wapiti nem gi):

- **`normalize_target(t)`** — **garante uma URL**: prefixa `http://` se o usuário
  digitar só o domínio.
- **`validate_target(t)`** — exige uma URL http/https válida (`_URL_RE`), sem
  espaços.
- **`build_scan_cmd(target, profile_args, out_path) -> list[str]`** — argv em
  **lista, nunca shell**: `wapiti -u URL -f json -o ARQUIVO --flush-session
  --verbose 0 <args do perfil>`. `--flush-session` começa do zero; `--verbose 0`
  silencioso; o perfil adiciona o `--scope`.
- **`parse_wapiti_json(data) -> list[Finding]`** — lê
  `data["vulnerabilities"] = {Categoria: [{method, path, info, level, parameter},
  …]}`; nunca levanta. Converte o **nível** (criticidade 0-4) do wapiti em
  severidade canônica via `_LEVEL_SEV` (`4→critical, 3→high, 2→medium, 1→low,
  0→info`). **Ordena por severidade** (`_SEV_ORDER`) e depois por categoria.
- **`counts_by_severity(findings)`** — contagem por severidade.

Parte que toca o sistema:

- **`run_scan(target, profile_id, *, timeout=900, handle=None) -> ScanResult`** —
  valida → checa disponibilidade → roda via `handle.run` (cancelável) ou
  `proc.run` dentro de um `TemporaryDirectory` (o relatório JSON é escrito lá,
  lido por `_read_json` e depois descartado). `res.ran = data is not None`
  distingue "rodou sem achados" de "falhou".

## Perfis (`PROFILES`, default `padrao`) — escopo do crawler

| id | rótulo | `--scope` | alcance |
|---|---|---|---|
| `rapida` | Rápida | `page` | só a página informada |
| `padrao` | Padrão | `folder` | a pasta da URL (mesmo diretório) |
| `completa` | Completa | `domain` | o domínio inteiro (lento/intrusivo) |

## Relatórios / permissões

- **`save_report`** → `~/.local/share/vigia-web/web-<ts>.json`, **0600**. O JSON
  cru do wapiti (`res.raw`) **não** vai no JSON salvo — alimenta o **Exportar**.
- **`result_to_text(r)`** → laudo TXT (`[SEVERIDADE] categoria · Em: método
  caminho (param) · info`).
- **`list_recent_reports(limit=20)`** → mais novos primeiro.
- **Central de Relatórios** (`_record_event`): evento resumo (`category="scan"`,
  severidade = a do pior achado) + um evento `category="finding"` por achado
  `critical/high/medium`. Falha engolida.

## GUI (`page.py`)

`build_content()` = `gate.build_gated(_build_tool)`. `ViewSwitcher` + `ViewStack`,
abas **Varredura** / **Histórico** / **Sobre**:

- **Varredura** (`_ScanView`): entrada de URL, `ComboRow` de perfil (Escopo),
  botões **Escanear** (vira **Cancelar** durante o scan) e **Exportar**. Scan em
  `threading.Thread` → `GLib.idle_add`. Achados em linhas com severidade colorida,
  ordenados por gravidade.
- **Histórico** / **Sobre** (perfis por escopo, pasta de relatórios, **Uso
  responsável** + revogação do termo).

## Limitações

- Cobertura limitada ao que o crawler alcança dentro do `--scope`.
- Envia **dados de teste** ao alvo — evitar produção com dados reais sem controle;
  preferir homologação/laboratório.
- `timeout` 900 s; escopo `domain` pode levar minutos.
- Achados exigem revisão humana (falso-positivo possível).

## Testes

`tests/red/test_web_backend.py` — **13 testes**: `normalize_target`
(prefixa http), `validate_target`, `build_scan_cmd` (argv-lista, `--scope`,
`-f json`), `parse_wapiti_json` (mapeamento nível→severidade, ordenação, JSON
inválido), `counts_by_severity` e relatórios. Rodam headless (sem wapiti nem GTK).
