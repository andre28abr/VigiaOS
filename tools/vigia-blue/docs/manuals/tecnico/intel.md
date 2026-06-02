# Vigia Intel — manual técnico

Módulo de **Threat Intelligence** do **VigiaBlue**. **Offline-first**: em vez de
depender de rede + API keys, mantém uma **base local de IOCs** e **checa
indicadores** contra ela. Importa de texto puro, **OTX** (pulse) e **MISP**
(event) a partir de arquivos que o usuário baixou — sem chamadas de rede.

## Arquivos

```
tools/vigia-blue/src/vigia_blue/modules/intel/
├── __init__.py
├── backend.py     # classificação + checagem + import + base (PURO/testável)
└── page.py        # GUI: Verificar / IOCs / Sobre

tests/blue/test_intel_backend.py   # 19 testes
tools/vigia-blue/docs/manuals/{leigo,tecnico}/intel.md
```

## Backend (`backend.py`)

Modelo: `IOC(type, value, source, note, added_at)` e `Match(indicator, ioc)`.
Tipos: `ip | domain | url | hash | email | other`.

Puro/testável:
- **`detect_type(s) -> (tipo, valor_normalizado)`** — regex: hash (32/40/64 hex),
  IPv4, URL (`http(s)://`), e-mail, domínio; senão `other`. Normaliza
  (lowercase em domínio/URL/e-mail/hash).
- **`check(indicadores, iocs) -> list[Match]`** — o **coração**: indexa a base por
  `(tipo, valor)` e casa cada indicador normalizado. URL também extrai o host
  (`_url_host`) e testa contra IOCs de **domínio**.
- **`import_plain(texto)`** — 1 linha/indicador, ignora vazias e `#`, dedupe.
- **`parse_otx_pulse(json)`** — lê `indicators[]` de um pulse do AlienVault OTX.
- **`parse_misp_event(json)`** — lê `Event.Attribute[]` de um evento MISP.

Base local (0600, via `vigia_common.state`):
- **`load_iocs()` / `save_iocs(iocs)`** — `~/.local/share/vigia-intel/iocs.json`.
- **`add_iocs(novos) -> int`** — mescla, dedupe por `(tipo, valor)`, carimba
  `added_at`, retorna quantos eram novos.
- **`remove_ioc(valor)`** / **`stats(iocs?)`** (contagem por tipo + total).

## GUI (`page.py`)

`build_content()` → `ToolbarView` + `ViewSwitcher` (Verificar / IOCs / Sobre).
- **Verificar** (`_CheckView`): `Gtk.TextView` (cola indicadores) → `check()` →
  `ExpanderRow` por match (ícone/pílula de aviso; expande Tipo/Valor/Fonte/Nota).
  Resumo "N de M casaram (base com K IOCs)".
- **IOCs** (`_IocsView`): adicionar 1 (tipo auto via `normalize`), **importar de
  arquivo** (`Gtk.FileDialog` → tenta `parse_otx_pulse`, senão `parse_misp_event`,
  senão `import_plain`), lista a base com remover, e stats no cabeçalho.
- As duas views se conhecem (`set_iocs_view`) para futura sincronização.

## Privilégio / LGPD

- Roda **sem root**; só toca o diretório do usuário. Base **0600**.
- Checagem **100% offline** — não vaza os indicadores consultados para serviços
  externos (relevante: consultar IOC em serviço público revela o que você está
  investigando).

## Pendências (próximos passos)

1. **Fetch online opcional** do OTX/MISP via API key (guardada com segurança),
   mantendo o offline como padrão.
2. Cruzar automaticamente os alertas do Vigia SIEM (IPs/hashes) com a base.
3. Expiração/validade de IOCs (TTL) e marcação de falso-positivo.
