# Antivirus

## Em uma frase

Wrapper GTK4 do **ClamAV** que substitui o `clamtk` (UI envelhecida) com
interface libadwaita moderna: scan on-demand com streaming de output, base
de assinaturas com freshclam e historico de reports JSON em modo 0600.

## O que envolve

| Item | Detalhe |
|---|---|
| Pacotes wrap | `clamav`, `clamav-update` |
| Versao | 0.1.1 |
| App ID | `br.com.vigia.Antivirus` |
| Privilegios | `pkexec freshclam` (so pra atualizar base) |
| Engine | clamscan standalone (NAO clamdscan/daemon nesta v0.1) |
| Modulo | `vigia_antivirus` |
| Reports | `~/.local/share/vigia-antivirus/scan-<timestamp>.json` (0600) |

## Arquitetura interna

```
vigia_antivirus/
├── backend.py          # DbInfo, scan_async, update_db_blocking
├── window.py           # build_content() -> Adw.ToolbarView 3 tabs
└── tabs/
    ├── scan.py         # Escolha de alvo + streaming output
    ├── database.py     # Update via freshclam + historico de scans
    └── about.py        # Manual didatico
```

Reports salvos como JSON serializado em
`~/.local/share/vigia-antivirus/` (dir 0700, arquivos 0600 — LGPD).
Estrutura do report:

```json
{
  "target": "/home/andre/Downloads",
  "started_at": "2026-05-28T15:30:00",
  "scanned_files": 1247,
  "scanned_dirs": 89,
  "infected_files": 0,
  "data_scanned": "412.34 MB",
  "elapsed_sec": 87.2,
  "findings": []
}
```

## Comandos disparados

Detect status (sem root):

```bash
clamscan --version
# ClamAV 1.0.5/27365/Mon May 13 12:34:56 2026
systemctl is-active --quiet clamd@scan
systemctl is-active --quiet clamav-daemon
```

Atualizar base de assinaturas (pkexec):

```bash
pkexec freshclam
```

Scan on-demand (sem root, streaming):

```bash
clamscan -r --no-summary=no --bell=no /home/andre/Downloads
```

Exit codes do ClamAV (tratados pelo backend):
- `0` = limpo
- `1` = malware encontrado (tambem considerado sucesso de execucao)
- `2` = erro interno

## Tabs / Funcionalidades

| Tab | Funcao |
|---|---|
| **Scan** | Banner com idade da base + entry de path + 4 atalhos (Home, Downloads, Documents, /tmp) + streaming live de findings |
| **Base de dados** | Versao engine + DB + idade + botao `Atualizar base agora` (pkexec freshclam) + lista dos ultimos 5 scans |
| **Sobre** | Manual didatico (`AboutTab` padrao Vigia) |

## Streaming de findings

A tab Scan parseia o stdout linha-a-linha do `clamscan` enquanto roda.
Regex pra detectar finding:

```python
m = re.match(r"^(.+):\s+(\S+)\s+FOUND\s*$", line)
if m:
    result.findings.append(Finding(
        path=m.group(1),
        signature=m.group(2),
    ))
```

Sumario parseado apos linha `----------- SCAN SUMMARY`:
- `Scanned directories: N`
- `Scanned files: N`
- `Infected files: N`
- `Data scanned: X.YZ MB`

## Quando usar

- **Antes de mandar arquivo pra cliente Windows** (PDF, .docx baixado).
- **Periodicamente em Downloads/Documents** (1x/semana recomendado).
- **Servidor de arquivos LGPD** com material recebido de terceiros.
- **Maquina compartilhada** ou apos test em VM com binarios suspeitos.

## Limitacoes conhecidas

- **Sem quarentena visual** — findings sao listados; apaga/move manual.
- **Sem scheduled scans** via UI — use `systemctl enable clamav-clamonacc`
  ou cron pra agendamento.
- **Sem clamdscan** (daemon) nesta v0.1 — forca uso do `clamscan`
  standalone (~30s overhead por scan pra carregar base na memoria).
- **Sem real-time protection** — Linux desktop nao precisa.
- **Sem integracao com Activity Log** (alvo v0.3).
- `clamscan` pode dar falso-positivo em packers legitimos (UPX) e PUAs.

## Trecho de codigo relevante

Worker thread que dispara `clamscan` e streama findings:

```python
def scan_async(
    path: str,
    on_line: Callable[[str], None],
    on_done: Callable[[ScanResult], None],
    stop_flag: Callable[[], bool] | None = None,
) -> threading.Thread:
    def worker():
        result = ScanResult(target=path)
        result.started_at = datetime.now().isoformat(timespec="seconds")

        cmd = ["clamscan", "-r", "--no-summary=no", "--bell=no", path]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        for raw_line in proc.stdout or []:
            if stop_flag is not None and stop_flag():
                proc.terminate()
                result.error = "Scan cancelado pelo usuario."
                break
            line = raw_line.rstrip()
            on_line(line)  # callback streaming

            m = re.match(r"^(.+):\s+(\S+)\s+FOUND\s*$", line)
            if m:
                result.findings.append(
                    Finding(path=m.group(1), signature=m.group(2))
                )

        proc.wait(timeout=10)
        if not result.error:
            _save_report(result)  # JSON 0600
        on_done(result)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t
```

Parse de `clamscan --version`:

```python
# Output: "ClamAV 1.0.5/27365/Mon May 13 12:34:56 2026"
parts = line.split("/")
m = re.search(r"ClamAV\s+([\d.]+)", parts[0])
info.engine_version = m.group(1)
info.db_version = parts[1].strip()
info.last_update = parts[2].strip()
dt = datetime.strptime(info.last_update, "%a %b %d %H:%M:%S %Y")
info.last_update_epoch = int(dt.timestamp())
```

## Privacidade / LGPD

- **100% offline** — base baixada do mirror oficial ClamAV, nada vai
  pra nuvem.
- Reports JSON em `~/.local/share/vigia-antivirus/` com mode `0600`,
  diretorio com `0700`. Apenas o owner le.
- ClamAV processa bytes dos arquivos mas NAO transmite — seguro pra
  escanear documentos sensiveis.

## Referencias

- `man clamscan`, `man freshclam`
- Site oficial: https://www.clamav.net
- Docs: https://docs.clamav.net
