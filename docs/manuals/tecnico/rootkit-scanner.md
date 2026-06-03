# Rootkit Scanner

## Em uma frase

Wrapper GTK4 que unifica **chkrootkit** + **Rootkit Hunter (rkhunter)** —
os dois scanners clássicos pra busca de rootkits e backdoors no Linux —
em UI libadwaita com streaming de output e histórico de scans em JSON
0600.

## O que envolve

| Item | Detalhe |
|---|---|
| Pacotes wrap | `chkrootkit`, `rkhunter` |
| Versão | 0.2.0 (rewrite pattern Antivirus) |
| App ID | `br.com.vigia.RootkitScanner` |
| Privilégios | `pkexec` pra ambos os scans (precisam ler `/etc`, `/dev`, `/proc`) |
| Módulo | `vigia_rootkit` |
| Reports | `~/.local/share/vigia-rootkit/scans/<scanner>-<timestamp>.json` (0600) |

## Arquitetura interna

```
vigia_rootkit/
├── backend.py          # scan_chkrootkit_async, scan_rkhunter_async, parsers
├── window.py           # build_content() -> Adw.ToolbarView 4 tabs
└── tabs/
    ├── chkrootkit.py   # Scan rapido (~30s)
    ├── rkhunter.py     # Scan completo (2-5min, 200+ checks)
    ├── history.py      # Lista reports anteriores
    └── about.py        # Manual didatico
```

Reports JSON são escritos em `~/.local/share/vigia-rootkit/scans/` com
`mode 0600`, dir `0700`. Limite de `raw_output` armazenado: 256 KB por
report (truncado).

## Comandos disparados

Detect versões (sem root):

```bash
chkrootkit -V
rkhunter --version
```

Scan chkrootkit (rápido, ~30s):

```bash
pkexec chkrootkit
```

Scan Rootkit Hunter (completo, 2-5min):

```bash
pkexec rkhunter --check --skip-keypress --no-mail-on-warning --rwo
```

Flags do rkhunter:
- `--check` — roda todos os checks (200+)
- `--skip-keypress` — sem `[Press Enter to continue]`
- `--no-mail-on-warning` — não tenta mandar email
- `--rwo` — Report Warnings Only (filtra OKs)

## Tabs / Funcionalidades

| Tab | Função |
|---|---|
| **chkrootkit** | Banner status + 2 botões (Iniciar / Parar) + log streaming + summary final |
| **Rootkit Hunter** | Mesmo pattern, scan mais demorado |
| **Histórico** | Lista de reports anteriores (recents-first), abre detalhes ao clicar |
| **Sobre** | Manual didático |

## Parsers

### chkrootkit

```python
_CHKR_TEST_RE = re.compile(r"^Checking\s+`?([^'`]+)'?\.{3}\s*(.*)$")

def _parse_chkrootkit_line(line: str) -> Finding | None:
    m = _CHKR_TEST_RE.match(line.strip())
    if not m:
        return None
    test, status = m.group(1), m.group(2).strip()
    status_lower = status.lower()
    if "infected" in status_lower and "not infected" not in status_lower:
        return Finding(test=test, severity="INFECTED", detail=status)
    if "you have" in status_lower or "warning" in status_lower:
        return Finding(test=test, severity="WARNING", detail=status)
    if "vulnerable" in status_lower:
        return Finding(test=test, severity="WARNING", detail=status)
    return None
```

### rkhunter

```python
_RKH_BRACKET_RE = re.compile(r"^(.+?)\s+\[\s*(\S+)\s*\]\s*$")
# ex: "Checking for rootkits  [ Warning ]"

def _parse_rkhunter_line(line: str) -> Finding | None:
    s = line.strip()
    m = _RKH_BRACKET_RE.match(s)
    if m:
        test, status = m.group(1).strip(), m.group(2).strip()
        if status.lower() == "warning":
            return Finding(test=test, severity="WARNING", detail=status)
        if status.lower() in ("infected", "compromised"):
            return Finding(test=test, severity="INFECTED", detail=status)
    if s.startswith("Warning:"):
        return Finding(test="rkhunter-warning", severity="WARNING",
                       detail=s[len("Warning:"):].strip())
    return None
```

## Streaming via pkexec

Pattern compartilhado entre os 2 scanners (`_run_scan_streaming`):

```python
def _run_scan_streaming(
    scanner_name: str,
    cmd: list[str],
    parser: Callable[[str], Finding | None],
    on_line: Callable[[str], None],
    on_done: Callable[[ScanResult], None],
    stop_flag: Callable[[], bool] | None,
) -> None:
    result = ScanResult(scanner=scanner_name)
    result.started_at = datetime.now().isoformat(timespec="seconds")

    proc = subprocess.Popen(
        ["pkexec"] + cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    for raw_line in proc.stdout or []:
        if stop_flag is not None and stop_flag():
            proc.terminate()
            result.cancelled = True
            break
        line = raw_line.rstrip()
        on_line(line)  # UI streaming
        if line.strip().startswith("Checking"):
            result.tests_run += 1
        finding = parser(line)
        if finding is not None:
            result.findings.append(finding)
            if finding.severity == "INFECTED":
                result.infected_count += 1
            elif finding.severity == "WARNING":
                result.warnings_count += 1

    if proc.returncode in (126, 127):
        result.error = "Autenticacao cancelada (pkexec)."
        result.cancelled = True

    if not result.cancelled and not result.error:
        _save_report(result)
    on_done(result)
```

## Quando usar

- **Após comportamento anômalo** do sistema (alto uso de CPU sem causa,
  conexões de rede estranhas, arquivos modificados).
- **Periodicamente** (1x/mês) como audit baseline.
- **Após `sudo dnf upgrade` major** do sistema.
- **Combinado com File Integrity** (AIDE) pra cross-check de mudanças
  em binários.

## Interpretando resultados

- **Limpo**: nenhum sinal. Sistema OK.
- **Warning**: possível falso positivo. Causas comuns:
  - Arquivos modificados após `sudo dnf upgrade`
  - Módulos proprietários (NVIDIA, VirtualBox)
  - Configs SSH OK no contexto específico
- **Infected**: alta probabilidade de comprometimento.
  1. Desconectar da rede
  2. Salvar o report (está em `~/.local/share/vigia-rootkit/scans/`)
  3. Cruzar com Vigia File Integrity (AIDE)
  4. Considerar reinstalar

## Limitações conhecidas

- chkrootkit e rkhunter são **detecção baseada em assinaturas conhecidas**
  — não pegam rootkits zero-day ou customizados.
- rkhunter gera **muitos falsos-positivos** em sistemas modernos
  (esperado — atualize `rkhunter.dat` periodicamente).
- Scans precisam de pkexec a cada execução (sem cache de auth).
- Limite de `raw_output` salvo: 1 MB em memória, 256 KB persistido.

## Privacidade / LGPD

- 100% offline.
- Reports JSON em `~/.local/share/vigia-rootkit/scans/` com `mode 0600`.
- Estrutura do report:

```json
{
  "scanner": "chkrootkit",
  "started_at": "2026-05-28T15:30:00",
  "tests_run": 47,
  "warnings_count": 2,
  "infected_count": 0,
  "elapsed_sec": 28.4,
  "cancelled": false,
  "findings": [
    {"test": "ifpromisc", "severity": "WARNING", "detail": "..."}
  ],
  "raw_output": "..."
}
```

## Referências

- `man chkrootkit`, `man rkhunter`
- chkrootkit: http://www.chkrootkit.org/
- Rootkit Hunter: https://rkhunter.sourceforge.net/
