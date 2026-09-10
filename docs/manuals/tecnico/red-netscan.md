# Vigia Network Scanner — manual técnico

Módulo de **Varredura & Descoberta** do **VigiaRed**. Wrapper do CLI `nmap`:
reconhecimento **ATIVO** (conecta nas portas do alvo, ≠ Recon passivo). Saída em
XML (`-oX -`), parseada com a stdlib. Por padrão roda **sem root** (TCP connect,
`-sT`); o **Modo admin** (pkexec) libera SYN (`-sS`), UDP (`-sU`) e detecção de
SO (`-O`/`-A`).

> **Pacote:** vigia-red 0.6.2 · **Status:** `pronto`. Padrão do ecossistema:
> *backend puro/testável + `page.py` ligado via `Module.impl`*, atrás do portão
> de termo de uso (`gate.build_gated`). Usa o runner cancelável compartilhado
> `vigia_red.runner.ScanProcess`.

## Arquivos

```
tools/vigia-red/src/vigia_red/modules/netscan/
├── __init__.py     # mínimo (sem gi)
├── backend.py      # perfis + validação + cmd + parser XML + relatórios (PURO)
└── page.py         # GUI: build_content() → abas Varredura/Histórico/Sobre

tests/red/test_netscan_backend.py   # 36 testes
```

## Dependência

- **`nmap`** (pacote `nmap` no Fedora, gerenciador `rpm`). `nmap_available()` =
  `shutil.which("nmap")`. Roda sem root no perfil padrão (TCP connect).

## Backend (`backend.py`)

### Validação do alvo (puro)

- **`normalize_target(t)`** — tira esquema e ponto final.
- **`validate_target(t)`** — aceita IP/CIDR (`ipaddress.ip_network`), **faixa de
  octetos do nmap** (`_OCTET_RANGE_RE`, ex.: `192.168.0-255.1`,
  `10.0.0.1,5,10-20`) ou **domínio** (`_DOMAIN_RE`, sem `/`).
- **`estimated_hosts(t)`** — nº de endereços cobertos (CIDR ou faixa de octetos).
- **`network_too_large(t)`** — bloqueia acima de **`MAX_HOSTS = 1024`**. Isso
  fecha um buraco antigo: labels tipo `1-255` passavam pela regex de domínio e a
  guarda só olhava CIDR — `1-255.1-255.1-255.1-255` (~4 bilhões de hosts) era
  aceito. Agora a faixa é **contada** octeto a octeto (`_octet_count`).
- **`is_ipv6(t)`** — decide se acrescenta `-6` ao comando (sem ele o nmap não
  resolve IPv6).
- **`validate_ports(ports)`** — vazio (usa o perfil) ou lista/faixa 1-65535
  (`_PORTS_RE`, ex.: `80,443,8000-8100`).

### Command builder (puro)

**`build_scan_cmd(target, profile, *, elevated=False, ports="", scripts="")`** —
argv em **lista, nunca shell**; `pkexec` na frente quando `elevated`. Regras:

- `-sn` (ping sweep): `nmap [-6] -sn -T4 -oX - alvo`.
- Base: `nmap [-6] -Pn --open -T4 -oX -`.
- **Sem admin**: remove técnicas root-only (`-sS`/`-sU`/`-O`/`-A`) e força `-sT`.
- **Com admin**: respeita a técnica do perfil.
- Portas custom (`-p`) têm prioridade sobre as do perfil; `--script` só se houver
  conjunto NSE.

### Perfis (`PROFILES`, default `padrao`)

| id | rótulo | técnica | admin? |
|---|---|---|---|
| `top` | Top serviços | `--top-ports 20 -sV` | não |
| `rapida` | Rápida | `-F` | não |
| `padrao` | Padrão | 1000 portas `-sV` | não |
| `web` | Web | `-p 80,443,8080,8443,8000,3000,5000 -sV` | não |
| `completa` | Completa | `-p- -sV` | não |
| `pingsweep` | Descoberta de hosts | `-sn` | não |
| `furtiva` | Furtiva / SYN | `-sS -sV` | **sim** |
| `udp` | UDP comum | `--top-ports 50 -sU` | **sim** |
| `agressiva` | Agressiva | `-A` (versão+SO+scripts+traceroute) | **sim** |

Conjuntos NSE (`SCRIPTS`, default `none`): `default` (`-sC`), `vuln`
(vulnerabilidades conhecidas → CVE), `web` (`http-enum,http-title,http-headers`).

### Parser (puro)

**`parse_nmap_xml(xml_text) -> list[Host]`** — `ElementTree`; nunca levanta
(`ParseError` → lista vazia). Extrai endereço (ipv4/ipv6), hostname, estado,
`os/osmatch`, e cada `ports/port` com `state == "open"` (serviço/product/version
e scripts NSE como `"id: saída"`). `Host`/`Port` com `describe()`; `ScanResult`
expõe `open_ports` e `hosts_up`.

### Scan (toca o sistema)

**`run_scan(target, profile_id, *, elevated, ports, scripts, timeout=600,
handle=None) -> ScanResult`** — valida alvo/faixa/portas/disponibilidade,
bloqueia perfil admin sem `elevated`, roda via `handle.run` (cancelável) ou
`proc.run`. `res.ran = "<nmaprun" in out`. Se `handle` (um `ScanProcess`) for
passado, a varredura é **cancelável**.

## Runner cancelável / Modo admin

`vigia_red.runner.ScanProcess` roda o comando via `subprocess.Popen`; `cancel()`
encerra o processo numa thread daemon (não congela a GUI). Em modo admin (argv
começa com `pkexec`) o SIGTERM direto dá EPERM, então o cancel pede `pkexec kill`
(novo diálogo polkit). **pkexec, nunca sudo** — padrão do projeto.

## Relatórios / permissões

- **`save_report`** → `~/.local/share/vigia-netscan/scan-<ts>.json`, **0600**.
- **`result_to_text(r)`** (TXT legível) e o `raw_xml` do nmap alimentam o botão
  **Exportar** (TXT/XML). O XML cru **não** vai no JSON salvo.
- **`list_recent_reports(limit=20)`** → mais novos primeiro.
- **Preferências**: `load_prefs`/`save_prefs` em
  `~/.config/vigia-red/netscan.json` (**0600**) guardam perfil/script/portas/admin
  padrão.
- **Central de Relatórios**: `events.record("netscan", …, category="scan")` ao
  final de uma varredura com hosts. Falha engolida.

## GUI (`page.py`)

`build_content()` = `gate.build_gated(_build_tool)`. `ViewSwitcher` + `ViewStack`
com abas **Varredura** / **Histórico** / **Sobre**:

- **Varredura** (`_ScanView`): entrada de alvo, `ComboRow` de perfil, campo de
  portas, `ComboRow` de scripts NSE, switch **Modo admin**, botões **Escanear**
  (vira **Cancelar** durante o scan) e **Exportar**. Scan em `threading.Thread` →
  `GLib.idle_add`. Consome `handoff.take_scan_target()` no `map` (pré-preenche o
  IP vindo do Recon).
- **Histórico** / **Sobre** (com **Uso responsável** e revogação do termo).

## Limitações

- `MAX_HOSTS = 1024` — varreduras em massa são deliberadamente barradas.
- `timeout` 600 s; perfil **Completa**/**UDP** podem levar minutos.
- Detecção de SO/versão é heurística do nmap — pode errar.

## Testes

`tests/red/test_netscan_backend.py` — **36 testes**: normalização/validação de
alvo (IP/CIDR/faixa/domínio/IPv6), `network_too_large`/`_octet_count`,
`validate_ports`, `build_scan_cmd` (com/sem admin, portas, scripts, `-6`, ping
sweep), `parse_nmap_xml` (portas/SO/scripts, XML malformado) e relatórios.
