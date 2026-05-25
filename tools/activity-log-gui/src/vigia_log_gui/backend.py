"""Backend do Activity Log GUI: chama `vigia-log --output json-bundle` e parseia.

Dois modos:
- Sem `elevated`: roda `vigia-log` direto. Audit log e' inacessivel sem root,
  entao normalmente so 'journald' funcionara (e mesmo assim limitado ao user).
- Com `elevated=True`: prefixa com `pkexec` para acessar audit.log e
  journal do sistema. UM dialog polkit por refresh.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ActivityEvent:
    timestamp: str
    source: str
    severity: str
    narrative: str
    payload: dict = field(default_factory=dict)


@dataclass
class ActivityCorrelation:
    kind: str
    severity: str
    timestamp: str
    end: str
    summary: str
    contributing_count: int


@dataclass
class ActivityBundle:
    version: int = 0
    generated_at: str = ""
    sources: list[str] = field(default_factory=list)
    events: list[ActivityEvent] = field(default_factory=list)
    correlations: list[ActivityCorrelation] = field(default_factory=list)
    raw_error: str = ""

    def has_data(self) -> bool:
        return bool(self.events) or bool(self.correlations)


# ============================================================
# Sanity
# ============================================================


def vigia_log_installed() -> bool:
    return shutil.which("vigia-log") is not None


def detect_available_sources() -> set[str]:
    """Quais sources fazem sentido oferecer no UI."""
    available: set[str] = set()
    if Path("/var/log/audit/audit.log").exists() or shutil.which("ausearch"):
        available.add("audit")
    if shutil.which("journalctl"):
        available.add("journald")
    if Path("/var/log/fail2ban.log").exists() or shutil.which("fail2ban-server"):
        available.add("fail2ban")
    return available


# ============================================================
# Run vigia-log
# ============================================================


def run_bundle(
    sources: list[str],
    elevated: bool = False,
    limit: int = 500,
    min_severity: str | None = None,
    timeout: int = 60,
) -> ActivityBundle:
    """Executa `vigia-log --output json-bundle` e retorna ActivityBundle.

    Se elevated=True, prefixa com `pkexec` (UM dialog polkit pra todas as fontes).
    """
    bundle = ActivityBundle()

    if not vigia_log_installed():
        bundle.raw_error = (
            "Binario `vigia-log` nao encontrado no PATH.\n\n"
            "Instale com:\n"
            "  cd tools/activity-log\n"
            "  cargo build --release\n"
            "  sudo install -m 0755 target/release/vigia-log /usr/local/bin/"
        )
        return bundle

    if not sources:
        bundle.raw_error = "Nenhuma fonte selecionada."
        return bundle

    cmd: list[str] = []
    if elevated:
        cmd.append("pkexec")
    cmd.append("vigia-log")
    cmd += ["--output", "json-bundle"]
    cmd += ["--limit", str(limit)]
    if min_severity:
        cmd += ["--min-severity", min_severity]
    cmd += ["--sources"] + list(sources)

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        bundle.raw_error = f"vigia-log demorou mais de {timeout}s. Tente reduzir --limit ou desligar sources."
        return bundle
    except FileNotFoundError:
        bundle.raw_error = "pkexec ou vigia-log nao encontrado."
        return bundle

    if result.returncode in (126, 127):
        bundle.raw_error = "Autenticacao cancelada."
        return bundle

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        bundle.raw_error = f"vigia-log retornou codigo {result.returncode}:\n\n{stderr[:600]}"
        return bundle

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        bundle.raw_error = f"JSON invalido do vigia-log: {e}"
        return bundle

    return _parse_bundle(data)


def _parse_bundle(data: dict) -> ActivityBundle:
    bundle = ActivityBundle()
    bundle.version = int(data.get("version", 0))
    bundle.generated_at = str(data.get("generated_at", ""))
    bundle.sources = list(data.get("sources", []) or [])

    for raw in data.get("events", []) or []:
        bundle.events.append(ActivityEvent(
            timestamp=str(raw.get("timestamp", "")),
            source=str(raw.get("source", "")),
            severity=str(raw.get("severity", "routine")),
            narrative=str(raw.get("narrative", "")),
            payload=raw.get("payload", {}) or {},
        ))

    for raw in data.get("correlations", []) or []:
        bundle.correlations.append(ActivityCorrelation(
            kind=str(raw.get("kind", "")),
            severity=str(raw.get("severity", "routine")),
            timestamp=str(raw.get("timestamp", "")),
            end=str(raw.get("end", "")),
            summary=str(raw.get("summary", "")),
            contributing_count=int(raw.get("contributing_count", 0)),
        ))

    return bundle


# ============================================================
# Helpers de severidade
# ============================================================


SEVERITY_ORDER = {"routine": 0, "interesting": 1, "suspicious": 2}


def severity_at_least(actual: str, minimum: str) -> bool:
    return SEVERITY_ORDER.get(actual, 0) >= SEVERITY_ORDER.get(minimum, 0)
