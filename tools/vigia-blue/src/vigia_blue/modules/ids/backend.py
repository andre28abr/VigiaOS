"""Backend do Vigia IDS — painel para o IDS de rede Suricata.

Wrapper de leitura do **`eve.json`** do Suricata (formato JSONL — um objeto JSON
por linha). Dois modos:
- **Ler um `eve.json`** já existente (de um Suricata em execução, normalmente em
  `/var/log/suricata/eve.json`) — não exige o Suricata instalado.
- **Analisar um `.pcap`** rodando o Suricata sobre ele (exige `suricata`).

Em ambos, parseia os eventos `event_type=="alert"` e os apresenta como alertas
triados por severidade — mesmo padrão visual do Vigia SIEM/YARA.

Partes PURAS (testáveis headless, sem suricata e sem gi):
- `parse_eve(jsonl)` — parser do eve.json (só os alertas).
- `map_severity(n)` — severidade Suricata (1=alta) → escala do projeto.
- `build_pcap_cmd(pcap, outdir)` — argv do suricata (lista, nunca shell).
"""

from __future__ import annotations

import json
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from vigia_common import proc
from vigia_common.state import load_json, save_json_0600

DATA_DIR = Path.home() / ".local" / "share" / "vigia-ids"
REPORTS_DIR = DATA_DIR

# Caminhos comuns do eve.json de um Suricata em execução.
DEFAULT_EVE_PATHS = [
    Path("/var/log/suricata/eve.json"),
    Path("/var/log/suricata/eve.jsonl"),
]

SEVERITY_RANK = {"info": 0, "baixo": 1, "suspeito": 2, "alto": 3, "critico": 4}


@dataclass
class Alert:
    timestamp: str
    signature: str
    category: str
    severity: str          # info | baixo | suspeito | alto
    src: str               # ip:porta
    dest: str              # ip:porta
    proto: str
    sid: int = 0


@dataclass
class IdsResult:
    alerts: list[Alert] = field(default_factory=list)
    source: str = ""
    total_lines: int = 0
    elapsed_sec: float = 0.0
    error: str = ""
    started_at: str = ""


# ============================================================
# Sanity
# ============================================================


def suricata_available() -> bool:
    return shutil.which("suricata") is not None


def find_eve() -> Path | None:
    """Primeiro eve.json existente nos caminhos padrão (ou None)."""
    for p in DEFAULT_EVE_PATHS:
        if p.is_file():
            return p
    return None


# ============================================================
# Parser (puro)
# ============================================================


def _safe_int(v: object, default: int = 0) -> int:
    try:
        return int(v)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return default


def map_severity(sev: object) -> str:
    """Severidade do Suricata (1=alta, 2=média, 3+=baixa) → escala do projeto."""
    n = _safe_int(sev, default=2)
    if n <= 1:
        return "alto"
    if n == 2:
        return "suspeito"
    if n == 3:
        return "baixo"
    return "info"


def _endpoint(ip: object, port: object) -> str:
    ip_s = str(ip or "").strip()
    if not ip_s:
        return ""
    p = _safe_int(port, default=0)
    return f"{ip_s}:{p}" if p else ip_s


def parse_eve(text: str) -> list[Alert]:
    """Parseia o eve.json (JSONL). Mantém só `event_type=="alert"`. Nunca crasha."""
    out: list[Alert] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(obj, dict) or obj.get("event_type") != "alert":
            continue
        a = obj.get("alert", {})
        if not isinstance(a, dict):
            a = {}
        out.append(Alert(
            timestamp=str(obj.get("timestamp", "")),
            signature=str(a.get("signature", "")) or "(sem assinatura)",
            category=str(a.get("category", "")),
            severity=map_severity(a.get("severity")),
            src=_endpoint(obj.get("src_ip"), obj.get("src_port")),
            dest=_endpoint(obj.get("dest_ip"), obj.get("dest_port")),
            proto=str(obj.get("proto", "")),
            sid=_safe_int(a.get("signature_id")),
        ))
    return out


# ============================================================
# Command builder (puro)
# ============================================================


def build_pcap_cmd(pcap: Path | str, outdir: Path | str) -> list[str]:
    """Argv do suricata p/ analisar um pcap (lista — nunca shell string).

    `suricata -r <pcap> -l <outdir>` gera `eve.json` em `outdir`.
    """
    return ["suricata", "-r", str(pcap), "-l", str(outdir)]


# ============================================================
# Análise (toca disco / sistema)
# ============================================================


def _read_tail(path: Path, max_bytes: int = 4_000_000) -> str:
    """Lê o arquivo; se gigante, só a cauda (eve.json cresce sem parar)."""
    size = path.stat().st_size
    with open(path, "rb") as fh:
        if size > max_bytes:
            fh.seek(size - max_bytes)
            fh.readline()  # descarta linha parcial
        data = fh.read()
    return data.decode("utf-8", errors="replace")


def _finish(result: IdsResult, text: str, t0: float, max_alerts: int) -> IdsResult:
    alerts = parse_eve(text)
    result.total_lines = text.count("\n") + 1 if text else 0
    alerts.sort(key=lambda a: SEVERITY_RANK.get(a.severity, 0), reverse=True)
    result.alerts = alerts[:max_alerts]
    result.elapsed_sec = round(time.monotonic() - t0, 2)
    return result


def analyze_eve(path: Path | str, max_alerts: int = 2000) -> IdsResult:
    """Lê e parseia um eve.json existente. Nunca levanta."""
    result = IdsResult(source=str(path),
                       started_at=datetime.now().isoformat(timespec="seconds"))
    t0 = time.monotonic()
    p = Path(path)
    if not p.is_file():
        result.error = f"Arquivo não encontrado: {path}"
        return result
    try:
        text = _read_tail(p)
    except OSError as e:
        result.error = f"Não foi possível ler {path}: {e}"
        return result
    return _finish(result, text, t0, max_alerts)


def analyze_pcap(pcap: Path | str, timeout: int = 300,
                 max_alerts: int = 2000) -> IdsResult:
    """Roda o Suricata sobre um pcap e parseia o eve.json gerado."""
    result = IdsResult(source=str(pcap),
                       started_at=datetime.now().isoformat(timespec="seconds"))
    t0 = time.monotonic()
    if not suricata_available():
        result.error = "Suricata não está instalado."
        return result
    outdir = tempfile.mkdtemp(prefix="vigia-ids-")
    rc, out, err = proc.run(build_pcap_cmd(pcap, outdir), timeout=timeout)
    eve = Path(outdir) / "eve.json"
    if not eve.is_file():
        result.error = (err.strip() or "O Suricata não gerou eve.json.")[:400]
        result.elapsed_sec = round(time.monotonic() - t0, 2)
        return result
    try:
        text = _read_tail(eve)
    except OSError as e:
        result.error = f"Falha ao ler o eve.json gerado: {e}"
        return result
    return _finish(result, text, t0, max_alerts)


# ============================================================
# Relatórios (0600 + histórico) — padrão dos demais módulos
# ============================================================


def save_report(result: IdsResult) -> Path | None:
    if not result.started_at:
        return None
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_ts = result.started_at.replace(":", "-").replace(".", "_")
    path = REPORTS_DIR / f"analysis-{safe_ts}.json"
    data = {
        "started_at": result.started_at,
        "source": result.source,
        "total_lines": result.total_lines,
        "elapsed_sec": result.elapsed_sec,
        "error": result.error,
        "alerts": [
            {"timestamp": a.timestamp, "signature": a.signature,
             "category": a.category, "severity": a.severity, "src": a.src,
             "dest": a.dest, "proto": a.proto, "sid": a.sid}
            for a in result.alerts
        ],
    }
    return path if save_json_0600(path, data) else None


def list_recent_reports(limit: int = 20) -> list[dict]:
    if not REPORTS_DIR.is_dir():
        return []
    files = sorted(REPORTS_DIR.glob("analysis-*.json"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    out: list[dict] = []
    for f in files[:limit]:
        data = load_json(f)
        if isinstance(data, dict):
            data["_file"] = str(f)
            out.append(data)
    return out
