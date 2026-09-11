# Vigia Wireless — manual técnico

Módulo de **Wireless** do **VigiaRed**. Auditoria **DEFENSIVA** da **própria**
rede Wi-Fi: mede se a senha WPA/WPA2 resiste a um ataque de dicionário sobre um
handshake capturado. Wrapper da suíte **aircrack-ng**. Responde "minha senha
aguenta?", **não** serve para acessar rede alheia (Lei 12.737/2012). A auditoria
tem dois passos: (1) **captura** do handshake — feita FORA do app (modo monitor +
root); (2) **teste** do `.cap` contra a wordlist — o que o app roda (não toca em
rede nenhuma).

> **Pacote:** vigia-red 0.7.0 · **Status:** `pronto`. Padrão do ecossistema:
> *backend puro/testável + `page.py` via `Module.impl`*, atrás do portão de termo
> de uso (`gate.build_gated`). Usa o runner cancelável `vigia_red.runner.ScanProcess`.

## Arquivos

```
tools/vigia-red/src/vigia_red/modules/wireless/
├── __init__.py     # mínimo (sem gi)
├── backend.py      # validação + cmds captura/teste + parser + relatórios (PURO)
└── page.py         # GUI: build_content() → abas Auditar/Histórico/Sobre

tests/red/test_wireless_backend.py   # 20 testes
```

## Dependência

- **`aircrack-ng`** (registry `Dependency`, gerenciador `rpm`, pacote
  `aircrack-ng`). Detecção: `aircrack_available()` / `airodump_available()` =
  `shutil.which(...)`. A **captura** do handshake exige placa em modo monitor +
  root (airodump-ng/aireplay-ng); o **teste** só precisa do `.cap` e roda sem
  root.

## Backend (`backend.py`)

### Informativo / validação (puro)

- `list_wifi_interfaces()` — lê `/sys/class/net/<if>/{wireless,phy80211}`; nunca
  levanta.
- `validate_bssid(b)` — regex `AA:BB:CC:DD:EE:FF`. `validate_interface(i)` —
  `^[A-Za-z0-9_.-]{1,15}$`. `validate_channel(c)` — dígitos, 1–196.
- `validate_capture(path)` — arquivo existente com sufixo `.cap`/`.pcap`/`.pcapng`.

### Montadores do passo de CAPTURA (puro — rodam FORA do app)

Documentados no manual e na aba **Sobre**; exigem modo monitor + root.

- `build_airodump_cmd(iface, bssid, channel, out_prefix)` →
  `airodump-ng --bssid <b> --channel <c> -w <prefix> <iface>` — `--bssid` e
  `--channel` **travam a captura no próprio AP** (não varrem o espectro).
- `build_aireplay_deauth_cmd(iface, bssid, count="3")` →
  `aireplay-ng --deauth <n> -a <b> <iface>` — força reconexão de um cliente
  **da própria rede** para gerar o handshake mais rápido (derruba conexões: só na
  sua rede).

### Montador do TESTE (puro — o passo que o app roda)

- `build_aircrack_cmd(capture, wordlist, bssid="")` →
  `aircrack-ng -w <wordlist> [-b <bssid>] <capture>`. Argv em **lista, nunca
  shell**.

### Parsers (puro — nunca levantam)

- `parse_aircrack_output(text) -> (found, password)` — regex `KEY FOUND! [ … ]`.
- `capture_has_handshake(text)` — heurística: `False` para "no valid wpa
  handshakes found" / "got no data packets" / "no networks found".

### Execução (toca o sistema — só o teste)

`run_audit(capture, wordlist, *, bssid="", timeout=1800, handle=None) ->
AuditResult` — valida captura/wordlist/BSSID/disponibilidade, roda
`build_aircrack_cmd` via `handle.run` (cancelável) ou `proc.run`. Se a saída não
indicar handshake válido (`capture_has_handshake`), grava o resultado com erro
pedindo nova captura. Senão marca `ran=True` e extrai `found`/`password`.

## Runner cancelável

`vigia_red.runner.ScanProcess` roda via `subprocess.Popen`; `cancel()` encerra o
processo numa thread daemon sem congelar a GUI. Sem shell.

## Relatórios / permissões

- **`save_report`** → `~/.local/share/vigia-wireless/wireless-<ts>.json`, **0600**
  (via `save_json_0600`).
- **Minimização/LGPD**: `result_to_dict` **NÃO grava a senha em claro** — só
  `found`, `bssid`, `capture`, `wordlist` e tempos. A senha aparece apenas na tela
  e no export TXT (`result_to_text`); `raw` (saída do aircrack) não vai no JSON.
- **`list_recent_reports(limit=20)`** → mais novos primeiro.
- **Central de Relatórios**: `events.record("wireless", …, category="scan",
  severity="high" se a senha caiu, senão "ok")`. Falha engolida.

## GUI (`page.py`)

`build_content()` = `gate.build_gated(_build_tool)` — o termo (`consent.py`,
Lei 12.737/2012) destrava a ferramenta. Padrão dos módulos Red:
`ViewSwitcher` + `ViewStack` com abas **Auditar** (seletor de `.cap`, wordlist,
BSSID opcional; iniciar vira **Cancelar**; **Exportar**), **Histórico** e
**Sobre** (comandos do passo de captura documentados + Uso responsável +
revogação do termo). Trabalho pesado em `threading.Thread` → `GLib.idle_add`.

## Limitações

- O app **não captura** o handshake — esse passo (modo monitor + root) é externo,
  por escolha; o backend só monta os comandos.
- Cobertura = a wordlist usada; "não caiu" ≠ "inquebrável".
- Só WPA/WPA2 por dicionário; `timeout` 1800 s.
- Handshake incompleto/corrompido no `.cap` invalida o teste (o backend avisa).

## Testes

`tests/red/test_wireless_backend.py` — **20 testes**: `validate_bssid`/
`validate_interface`/`validate_channel`/`validate_capture`, `build_airodump_cmd`/
`build_aireplay_deauth_cmd`/`build_aircrack_cmd` (argv-lista, `-b`),
`parse_aircrack_output` (KEY FOUND) e `capture_has_handshake` (sem handshake). 
Rodam headless (sem aircrack-ng nem GTK).
