# Vigia Recon — manual técnico

Módulo de **Reconhecimento & OSINT** do **VigiaRed** (pentest educacional).
Wrapper do CLI `theHarvester`: dado um domínio autorizado, consulta fontes
públicas (transparência de certificados, DNS, buscadores) e devolve a superfície
externa — e-mails, subdomínios, IPs, URLs. **Passivo por princípio**: nunca toca
nos servidores do alvo, só lê o que já é público.

> **Pacote:** vigia-red 0.6.3 · **Status:** `pronto` (1º módulo real do Red).
> Segue o padrão do ecossistema: *backend puro/testável + `page.py` (GUI) ligado
> ao shell via `Module.impl`*. Portão de termo de uso (`gate.build_gated`) antes
> da ferramenta.

## Arquivos

```
tools/vigia-red/src/vigia_red/
├── consent.py          # aceite do termo (0600) — puro/testável
├── gate.py             # portão GTK reusável (termo → ferramenta)
├── handoff.py          # corredor Recon → Network Scanner (alvo pendente em memória)
└── modules/recon/
    ├── __init__.py     # mínimo (sem gi — mantém backend testável)
    ├── backend.py      # wrapper + validação + parser + relatórios (PURO)
    └── page.py         # GUI: build_content() → abas Investigar/Histórico/Sobre

tests/red/test_recon_backend.py   # 29 testes (normalização, validação, cmd, parser, auto-cura)
```

## Dependência

- **`theHarvester`** (CLI). `theharvester_available()` procura os binários
  `theHarvester` / `theharvester` / `theHarvester.py` no PATH. Sem ele, o backend
  não quebra — `run_recon` devolve `error` e a GUI mostra banner.
- Instalação (registry `Dependency`, gerenciador `pip`):
  `pipx install git+https://github.com/laramies/theHarvester.git`

## Backend (`backend.py`)

Partes **puras** (testadas sem `theHarvester` nem gi):

- **`normalize_domain(domain) -> str`** — remove esquema (`http://`), caminho,
  `user@`, `:porta` e espaços; reduz `www.dominio.com` → `dominio.com`.
- **`validate_domain(domain) -> bool`** — casa contra `_DOMAIN_RE` (rótulos
  alfanuméricos, ≥1 ponto, ≤253 chars). Valida **depois** de normalizar.
- **`build_harvester_cmd(domain, source_ids, out_basename, limit=500) -> list[str]`**
  — monta `theHarvester -d DOMÍNIO -b fonte1,fonte2 -l LIMITE -f BASE`. **Lista,
  nunca shell string** (convenção de segurança). `-f BASE` faz o theHarvester
  gravar `BASE.json`/`BASE.xml`.
- **`parse_harvester_json(data, domain) -> ReconResult`** — parser robusto do
  JSON. Extrai `emails`, `hosts` (aceita `"host"` ou `"host:ip"` — separa o IP),
  `ips`, `interesting_urls`/`urls`. `_clean()` deduplica (case-insensitive) e
  ordena. Nunca levanta com JSON inesperado.

Parte que toca o sistema:

- **`run_recon(domain, source_ids=None, limit=500, timeout=300) -> ReconResult`**
  — valida → checa disponibilidade → roda via `vigia_common.proc.run` (nunca
  levanta) dentro de um `TemporaryDirectory` → lê o JSON gravado → parseia →
  salva relatório. `res.ran = data is not None` distingue "rodou e não achou
  nada" de "falhou de verdade".

## Fontes OSINT (curadas, sem chave de API)

`SOURCES` lista as fontes **validadas no theHarvester 4.11.1** (key-free),
confirmadas na VM — `DEFAULT_SOURCE_IDS` usa todas:

| id | rótulo | conteúdo |
|---|---|---|
| `crtsh` | Certificados SSL (crt.sh) | subdomínios via transparência de certificados |
| `hackertarget` | HackerTarget | hosts e DNS |
| `rapiddns` | RapidDNS | subdomínios |
| `otx` | AlienVault OTX | inteligência de ameaças |
| `urlscan` | urlscan.io | subdomínios e URLs |
| `duckduckgo` | DuckDuckGo | busca por e-mails e hosts |

Fontes que exigem chave (shodan/github) ficam de fora do conjunto padrão.
`anubis`/`threatminer` saíram porque foram removidas do theHarvester.

### Auto-cura de fonte removida

O theHarvester **rejeita a busca inteira** se uma fonte do `-b` não existir na
versão instalada (`The following engines are not supported: {...}`). O backend
trata isso: se o JSON não foi gravado, `_unsupported_engines(text)` extrai por
regex as fontes recusadas, `run_recon` as remove da lista e **refaz a busca** só
com as boas (`out-retry`). Assim um módulo continua funcionando quando uma fonte
some numa versão futura.

## Relatórios / permissões

- **`save_report(result)`** → `~/.local/share/vigia-recon/recon-<ts>.json`,
  escrita atômica **0600** (LGPD — pode conter e-mails/hosts sensíveis), via
  `vigia_common.state.save_json_0600`.
- **`list_recent_reports(limit=20)`** → mais novos primeiro, descarta corrompidos.
- **Central de Relatórios**: ao final de um recon com resultado, grava um evento
  defensivo em `vigia_common.events.record("recon", …, category="recon",
  severity="info")` — aparece na seção **Relatórios** do VigiaOS. Falha de
  gravação é engolida (nunca derruba o scan).
- Offline por princípio: nada sai da máquina **exceto** as consultas do
  theHarvester às fontes públicas.

## GUI (`page.py`)

`build_content()` retorna `gate.build_gated(_build_tool)` — na 1ª execução exibe
o termo de uso (Lei 12.737/2012, `consent.py`); aceito uma vez, destrava **todos**
os módulos do Red. `_build_tool()` monta um `Adw.ToolbarView` com `ViewSwitcher`
+ `ViewStack`:

- **Investigar** (`_ReconView`): `Adw.EntryRow` (domínio), botão **Investigar** +
  `Gtk.Spinner`, banner se o theHarvester faltar. A busca roda em
  `threading.Thread` → `GLib.idle_add(self._apply, ...)` (não trava a UI). Cada
  categoria vira um `Adw.ExpanderRow` (`_category_expander`, cap 100 itens). Nos
  IPs, cada linha ganha um botão **Escanear** que chama `handoff.set_scan_target`
  e exibe um toast.
- **Histórico** (`_HistoryView`): `list_recent_reports()` → 1 linha por recon;
  abre o JSON no app padrão.
- **Sobre**: descrição, comando de instalação, pasta de relatórios, lista de
  fontes e **Uso responsável** (com **Revogar aceite do termo** →
  `consent.revoke()`).

Todo valor vindo de dados passa por `GLib.markup_escape_text` (linhas Adw usam
markup Pango).

## Handoff Recon → Network Scanner

`handoff.py` guarda um alvo "pendente" **em memória** (mesmo processo do app,
não persiste em disco). `set_scan_target(ip)` grava; `take_scan_target()`
devolve e limpa (consumo único). O Network Scanner consome no `map`.

## Limitações

- Resultado = o que as fontes públicas conheciam no momento; não é enumeração
  exaustiva.
- Sem fontes com chave de API (shodan/github) por padrão — deliberado (superfície
  mínima).
- `limit` padrão 500 por fonte; `timeout` 300 s.

## Testes

`tests/red/test_recon_backend.py` — **29 testes** cobrindo `normalize_domain`,
`validate_domain`, `build_harvester_cmd` (argv-lista), `parse_harvester_json`
(incluindo `host:ip`), `_clean`, `_unsupported_engines`/auto-cura e os
relatórios. Rodam headless (sem theHarvester nem GTK).
