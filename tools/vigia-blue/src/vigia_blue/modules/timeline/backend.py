"""Backend do Vigia Timeline — super-timeline forense com o plaso.

Wrapper do **plaso** (`log2timeline.py` + `psort.py`). Reconstrói a linha do
tempo de "o que aconteceu e quando" a partir de uma fonte (pasta, arquivo,
imagem). Três entradas:
- **Abrir export** `json_line` já pronto (parser puro — NÃO exige plaso).
- **Analisar um `.plaso`** existente (roda `psort.py`).
- **Gerar de uma fonte** (roda `log2timeline.py` + `psort.py` — lento, exige plaso).

Partes PURAS (testáveis headless, sem plaso e sem gi):
- `parse_psort_jsonl(text)` — parser do json_line do psort.
- `build_log2timeline_cmd(...)` / `build_psort_cmd(...)` — argv (lista, nunca shell).
"""

from __future__ import annotations

import json
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from vigia_common import proc


@dataclass
class Event:
    timestamp: str          # ISO datetime
    message: str
    data_type: str          # plaso data_type (ex.: fs:stat, syslog:line)
    source: str             # source_long / parser


@dataclass
class TimelineResult:
    events: list[Event] = field(default_factory=list)
    source: str = ""
    total: int = 0
    elapsed_sec: float = 0.0
    error: str = ""
    started_at: str = ""


# ============================================================
# Sanity (binários do plaso)
# ============================================================


def log2timeline_bin() -> str | None:
    for b in ("log2timeline.py", "log2timeline"):
        if shutil.which(b):
            return b
    return None


def psort_bin() -> str | None:
    for b in ("psort.py", "psort"):
        if shutil.which(b):
            return b
    return None


def plaso_available() -> bool:
    return log2timeline_bin() is not None and psort_bin() is not None


# ============================================================
# Command builders (puros)
# ============================================================


def build_log2timeline_cmd(storage: Path | str, source: Path | str,
                           bin_name: str | None = None) -> list[str]:
    """Argv do log2timeline (lista — nunca shell string).

    `log2timeline.py --status_view none <storage.plaso> <source>`.
    """
    b = bin_name or log2timeline_bin() or "log2timeline.py"
    return [b, "--status_view", "none", str(storage), str(source)]


def build_psort_cmd(storage: Path | str, output: Path | str,
                    fmt: str = "json_line", bin_name: str | None = None) -> list[str]:
    """Argv do psort (lista — nunca shell string).

    `psort.py -o json_line -w <output> <storage.plaso>`.
    """
    b = bin_name or psort_bin() or "psort.py"
    return [b, "-o", fmt, "-w", str(output), str(storage)]


# ============================================================
# Parser (puro)
# ============================================================


def _ts_from_micros(v: object) -> str:
    """Timestamp do plaso (inteiro, microssegundos desde 1970) → ISO. '' se inválido."""
    try:
        micros = int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return ""
    if micros <= 0:
        return ""
    try:
        dt = datetime.fromtimestamp(micros / 1_000_000, tz=timezone.utc)
        return dt.isoformat(sep=" ", timespec="seconds")
    except (OverflowError, OSError, ValueError):
        return ""


def parse_psort_jsonl(text: str, max_events: int = 5000) -> list[Event]:
    """Parseia a saída `-o json_line` do psort (um JSON por linha). Nunca crasha."""
    out: list[Event] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        ts = obj.get("datetime") or _ts_from_micros(obj.get("timestamp"))
        source = (obj.get("source_long") or obj.get("parser")
                  or obj.get("source_short") or "")
        out.append(Event(
            timestamp=str(ts or ""),
            message=str(obj.get("message", "") or ""),
            data_type=str(obj.get("data_type", "") or ""),
            source=str(source or ""),
        ))
        if len(out) >= max_events:
            break
    return out


# ============================================================
# Leitura de arquivo grande (timelines crescem muito)
# ============================================================


def _read_capped(path: Path, max_bytes: int = 8_000_000) -> str:
    size = path.stat().st_size
    with open(path, "rb") as fh:
        data = fh.read(max_bytes if size > max_bytes else size)
    return data.decode("utf-8", errors="replace")


# ============================================================
# Análise (toca disco / sistema)
# ============================================================


def analyze_psort_file(path: Path | str, max_events: int = 5000) -> TimelineResult:
    """Abre e parseia um export json_line já pronto. NÃO exige plaso."""
    result = TimelineResult(source=str(path),
                            started_at=datetime.now().isoformat(timespec="seconds"))
    t0 = time.monotonic()
    p = Path(path)
    if not p.is_file():
        result.error = f"Arquivo não encontrado: {path}"
        return result
    try:
        text = _read_capped(p)
    except OSError as e:
        result.error = f"Não foi possível ler {path}: {e}"
        return result
    result.events = parse_psort_jsonl(text, max_events)
    result.total = len(result.events)
    result.elapsed_sec = round(time.monotonic() - t0, 2)
    return result


def analyze_storage(storage: Path | str, timeout: int = 1200,
                    max_events: int = 5000) -> TimelineResult:
    """Roda o psort sobre um .plaso existente e parseia o json_line gerado."""
    result = TimelineResult(source=str(storage),
                            started_at=datetime.now().isoformat(timespec="seconds"))
    t0 = time.monotonic()
    if not psort_bin():
        result.error = "psort (plaso) não está instalado."
        return result
    outdir = tempfile.mkdtemp(prefix="vigia-timeline-")
    out = Path(outdir) / "timeline.jsonl"
    rc, _o, err = proc.run(build_psort_cmd(storage, out), timeout=timeout)
    if not out.is_file():
        result.error = (err.strip() or "O psort não gerou saída.")[:400]
        result.elapsed_sec = round(time.monotonic() - t0, 2)
        return result
    result.events = parse_psort_jsonl(_read_capped(out), max_events)
    result.total = len(result.events)
    result.elapsed_sec = round(time.monotonic() - t0, 2)
    return result


def run_timeline(source: Path | str, timeout: int = 1800,
                 max_events: int = 5000) -> TimelineResult:
    """Pipeline completo: log2timeline (extrai) + psort (ordena/exporta). Lento."""
    result = TimelineResult(source=str(source),
                            started_at=datetime.now().isoformat(timespec="seconds"))
    t0 = time.monotonic()
    if not plaso_available():
        result.error = "plaso (log2timeline + psort) não está instalado."
        return result
    tmpdir = tempfile.mkdtemp(prefix="vigia-timeline-")
    storage = Path(tmpdir) / "timeline.plaso"
    rc, _o, err = proc.run(build_log2timeline_cmd(storage, source), timeout=timeout)
    if not storage.is_file():
        result.error = (err.strip() or "log2timeline não gerou o storage.")[:400]
        result.elapsed_sec = round(time.monotonic() - t0, 2)
        return result
    out = Path(tmpdir) / "timeline.jsonl"
    rc2, _o2, err2 = proc.run(build_psort_cmd(storage, out), timeout=timeout)
    if not out.is_file():
        result.error = (err2.strip() or "psort não gerou saída.")[:400]
        result.elapsed_sec = round(time.monotonic() - t0, 2)
        return result
    result.events = parse_psort_jsonl(_read_capped(out), max_events)
    result.total = len(result.events)
    result.elapsed_sec = round(time.monotonic() - t0, 2)
    return result
