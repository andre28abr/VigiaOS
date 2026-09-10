# Vigia Vuln Scanner — manual técnico

Módulo de **Varredura & Vulnerabilidades** do **VigiaRed**. Wrapper do CLI
`nuclei`: aprofunda o que o Network Scanner achou rodando templates da comunidade
(CVEs, exposições, misconfigs) contra um alvo autorizado e classificando por
severidade. Saída em **JSONL** (`-jsonl`), parseada com a stdlib.

> **Pacote:** vigia-red 0.6.2 · **Status:** `pronto`. Padrão do ecossistema:
> *backend puro/testável + `page.py` via `Module.impl`*, atrás do portão de termo
> (`gate.build_gated`). Runner cancelável `vigia_red.runner.ScanProcess`.

## Arquivos

```
tools/vigia-red/src/vigia_red/modules/vuln/
├── __init__.py     # mínimo (sem gi)
├── backend.py      # perfis + validação + cmd + parser JSONL + relatórios (PURO)
└── page.py         # GUI: build_content() → abas Varredura/Histórico/Sobre

tests/red/test_vuln_backend.py   # 11 testes
```

## Dependência

- **`nuclei`** (ProjectDiscovery). `nuclei_available()` = `shutil.which("nuclei")`.
  Instalação (registry `Dependency`, gerenciador `source`):
  `go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest` (requer
  Go — `sudo dnf install golang`). Os **templates** são baixados pelo próprio
  nuclei na 1ª execução; se faltarem, o backend sugere `nuclei -update-templates`.

## Backend (`backend.py`)

Partes **puras** (testadas sem nuclei nem gi):

- **`normalize_target(t)`** / **`validate_target(t)`** — aceita URL
  (`_URL_RE`, http/https), domínio (`_DOMAIN_RE`) ou IP (`ipaddress.ip_address`).
- **`build_nuclei_cmd(target, profile_args) -> list[str]`** — argv em **lista,
  nunca shell**: `nuclei -target ALVO -jsonl -silent -nc <args do perfil>`.
  `-jsonl` (JSON Lines), `-silent` (só achados, sem banner/progresso), `-nc` (sem
  cor). **Sem `-disable-update-check`** — deixa o nuclei baixar os templates
  sozinho.
- **`parse_nuclei_jsonl(text) -> list[Finding]`** — 1 achado por linha JSON;
  ignora linhas que não começam com `{`; nunca levanta. Extrai `template-id`,
  `info.name`, `info.severity` (minúsculo), `info.tags`, `info.description`,
  `matched-at`, `host`. **Ordena por severidade** via `_SEV_ORDER`
  (`critical > high > medium > low > info > unknown`) e depois por nome.
- **`counts_by_severity(findings)`** — contagem por severidade (para o resumo).

Parte que toca o sistema:

- **`run_scan(target, profile_id, *, timeout=900, handle=None) -> ScanResult`** —
  valida → checa disponibilidade → roda via `handle.run` (cancelável) ou
  `proc.run`. O nuclei **sai 0 mesmo sem achados**, então
  `res.ran = rc == 0 or bool(findings)`; `rc != 0` sem achados = erro real
  (com dica especial para "no templates").

## Perfis (`PROFILES`, default `cves`)

| id | rótulo | args (tags/severidade) |
|---|---|---|
| `cves` | CVEs graves | `-tags cve -severity critical,high` |
| `padrao` | Padrão | `-tags cve,exposure,misconfig -severity critical,high,medium` |
| `exposicoes` | Exposições | `-tags exposure,exposed-panels,default-login` |
| `tech` | Tecnologias | `-tags tech` |
| `completa` | Completa | (sem filtro — todos os templates) |

## Relatórios / permissões

- **`save_report`** → `~/.local/share/vigia-vuln/vuln-<ts>.json`, **0600**.
  O JSONL cru (`res.raw`) **não** vai no JSON salvo — alimenta o **Exportar**.
- **`result_to_text(r)`** → laudo TXT (`[SEVERIDADE] nome (template) · Em: … ·
  descrição`).
- **`list_recent_reports(limit=20)`** → mais novos primeiro, descarta corrompidos.
- **Central de Relatórios**: `events.record` grava um evento resumo
  (`category="scan"`, severidade = a do pior achado) e, para cada achado
  `critical/high/medium`, um evento `category="finding"`. Falha engolida.

## GUI (`page.py`)

`build_content()` = `gate.build_gated(_build_tool)`. `ViewSwitcher` + `ViewStack`,
abas **Varredura** / **Histórico** / **Sobre**:

- **Varredura** (`_ScanView`): entrada de URL/domínio, `ComboRow` de perfil
  (Templates), botões **Escanear** (vira **Cancelar** durante o scan) e
  **Exportar**. Scan em `threading.Thread` → `GLib.idle_add`. Cada achado vira
  uma linha com severidade colorida; grupo **Achados** ordenado por gravidade.
- **Histórico** / **Sobre** (Templates, pasta de relatórios, **Uso responsável** +
  revogação do termo).

## Limitações

- Cobertura = os templates instalados; "zero achados" ≠ "seguro".
- `timeout` 900 s; perfil **Completa** pode levar minutos.
- Depende de o nuclei ter baixado os templates (1ª execução / `-update-templates`).
- Detecção baseada em assinatura de template — pode gerar falso-positivo; revisão
  humana necessária.

## Testes

`tests/red/test_vuln_backend.py` — **11 testes**: `validate_target`
(URL/domínio/IP), `build_nuclei_cmd` (argv-lista, flags), `parse_nuclei_jsonl`
(ordenação por severidade, linhas inválidas ignoradas), `counts_by_severity` e
relatórios. Rodam headless (sem nuclei nem GTK).
