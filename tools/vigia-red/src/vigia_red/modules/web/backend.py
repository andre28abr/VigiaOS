"""Backend do Vigia Web Scanner — vulnerabilidades de aplicações web (wapiti).

Completa o tripé do Red no nível da APLICAÇÃO web: dado uma URL autorizada, o
wapiti rastreia o site e testa falhas estilo OWASP (XSS, SQLi, inclusão de
arquivo, etc.). Saída em JSON (`-f json -o arquivo`), parseada com a stdlib.

Partes PURAS (testáveis sem wapiti, sem GTK):
- `normalize_target` / `validate_target` — exige uma URL (prefixa http:// se faltar).
- `build_scan_cmd(...)` — argv do wapiti (lista, nunca shell).
- `parse_wapiti_json(...)` — JSON do wapiti → achados ordenados por severidade.

Parte que toca o sistema:
- `run_scan(...)` — roda via runner cancelável + relatório 0600 + grava eventos.
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from vigia_common import proc
from vigia_common.state import load_json, save_json_0600

from ...runner import ScanProcess

DATA_DIR = Path.home() / ".local" / "share" / "vigia-web"
REPORTS_DIR = DATA_DIR


# ============================================================
# Perfis (escopo do rastreamento do wapiti)
# ============================================================


@dataclass(frozen=True)
class Profile:
    id: str
    label: str
    description: str
    args: tuple[str, ...]


PROFILES: list[Profile] = [
    Profile("rapida", "Rápida",
            "Só a página informada — rápido.",
            ("--scope", "page")),
    Profile("padrao", "Padrão",
            "A pasta da URL (mesmo diretório). Recomendado.",
            ("--scope", "folder")),
    Profile("completa", "Completa",
            "O domínio inteiro. Bem mais lento e intrusivo.",
            ("--scope", "domain")),
]
DEFAULT_PROFILE = "padrao"

SEVERITIES = ["critical", "high", "medium", "low", "info", "unknown"]
_SEV_ORDER = {s: i for i, s in enumerate(SEVERITIES)}
# wapiti: nível (criticidade) -> severidade canônica
_LEVEL_SEV = {4: "critical", 3: "high", 2: "medium", 1: "low", 0: "info"}


# ============================================================
# Dataclasses de resultado
# ============================================================


@dataclass
class Finding:
    category: str           # "Cross Site Scripting", "SQL Injection"…
    severity: str = "medium"
    method: str = ""
    path: str = ""
    info: str = ""
    parameter: str = ""


@dataclass
class ScanResult:
    target: str
    profile: str = ""
    findings: list[Finding] = field(default_factory=list)
    started_at: str = ""
    elapsed_sec: float = 0.0
    error: str = ""
    ran: bool = False
    raw: str = ""           # JSON cru (export) — não vai no JSON salvo

    @property
    def total(self) -> int:
        return len(self.findings)


# ============================================================
# Disponibilidade / validação
# ============================================================


def wapiti_available() -> bool:
    return shutil.which("wapiti") is not None


_URL_RE = re.compile(r"^https?://[^\s/$.?#][^\s]*$", re.IGNORECASE)


def normalize_target(t: str) -> str:
    """Garante uma URL: prefixa http:// se o usuário digitar só o domínio."""
    t = (t or "").strip()
    if t and not re.match(r"^https?://", t, re.IGNORECASE):
        t = "http://" + t
    return t


def validate_target(t: str) -> bool:
    t = normalize_target(t)
    return bool(t) and " " not in t and bool(_URL_RE.match(t))


# ============================================================
# Command builder (puro)
# ============================================================


def build_scan_cmd(target: str, profile_args: tuple[str, ...] | list[str],
                   out_path: Path | str) -> list[str]:
    """Monta o argv do wapiti (lista — nunca shell string).

    `-u URL`; `-f json -o ARQUIVO` saída JSON; `--flush-session` começa do zero;
    `--verbose 0` silencioso. O perfil adiciona o `--scope`.
    """
    return [
        "wapiti",
        "-u", target,
        "-f", "json", "-o", str(out_path),
        "--flush-session", "--verbose", "0",
        *profile_args,
    ]


# ============================================================
# Parser do JSON do wapiti (puro)
# ============================================================


def _sev_from_level(level) -> str:
    try:
        return _LEVEL_SEV.get(int(level), "medium")
    except (TypeError, ValueError):
        return "medium"


def parse_wapiti_json(data) -> list[Finding]:
    """Parseia o relatório JSON do wapiti. Nunca levanta.

    Formato: `{"vulnerabilities": {Categoria: [ {method, path, info, level,
    parameter}, … ], …}}`.
    """
    findings: list[Finding] = []
    if not isinstance(data, dict):
        return findings
    vulns = data.get("vulnerabilities")
    if not isinstance(vulns, dict):
        return findings
    for category, items in vulns.items():
        if not isinstance(items, list):
            continue
        for it in items:
            if not isinstance(it, dict):
                continue
            findings.append(Finding(
                category=str(category),
                severity=_sev_from_level(it.get("level", 2)),
                method=str(it.get("method", "")),
                path=str(it.get("path", "")),
                info=str(it.get("info", "")).strip(),
                parameter=str(it.get("parameter", "")),
            ))
    findings.sort(key=lambda f: (_SEV_ORDER.get(f.severity, 99),
                                 f.category.lower()))
    return findings


def counts_by_severity(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    return counts


def _read_json(path: Path):
    for cand in (path, path.with_suffix(".json")):
        try:
            if cand.is_file():
                return json.loads(cand.read_text(encoding="utf-8", errors="replace"))
        except (OSError, json.JSONDecodeError, ValueError):
            continue
    return None


def _last_line(text: str) -> str:
    for line in reversed((text or "").splitlines()):
        s = line.strip()
        if s:
            return s[:200]
    return ""


# ============================================================
# Scan (toca o sistema)
# ============================================================


def run_scan(
    target: str,
    profile_id: str = DEFAULT_PROFILE,
    *,
    timeout: int = 900,
    handle: ScanProcess | None = None,
) -> ScanResult:
    """Roda o wapiti no `target`. Nunca levanta; erros vão em `.error`."""
    tgt = normalize_target(target)
    res = ScanResult(
        target=tgt,
        profile=profile_id,
        started_at=datetime.now().isoformat(timespec="seconds"),
    )
    if not validate_target(tgt):
        res.error = ("Alvo inválido. Informe uma URL — ex.: "
                     "https://exemplo.com.br.")
        return res
    if not wapiti_available():
        res.error = "wapiti não está instalado."
        return res

    prof = next((p for p in PROFILES if p.id == profile_id), None)
    args = prof.args if prof else ()

    runner = handle.run if handle is not None else proc.run
    t0 = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="vigia-web-") as td:
        out = Path(td) / "report.json"
        rc, out_s, err = runner(build_scan_cmd(tgt, args, out), timeout=timeout)
        data = _read_json(out)
    res.elapsed_sec = round(time.monotonic() - t0, 2)

    if data is not None:
        res.raw = json.dumps(data, ensure_ascii=False)
        res.findings = parse_wapiti_json(data)
        res.ran = True
    else:
        res.error = _last_line(err) or _last_line(out_s) or (
            f"O wapiti não gerou relatório (código {rc}).")

    save_report(res)
    _record_event(res)
    return res


def _record_event(res: ScanResult) -> None:
    try:
        from vigia_common import events
        if res.error:
            return
        worst = res.findings[0].severity if res.findings else "ok"
        events.record(
            "web", f"Web: {res.total} achado(s)", category="scan",
            severity=worst, ref=res.target,
            payload={"profile": res.profile, "count": res.total})
        for f in res.findings:
            if events.normalize_severity(f.severity) in (
                    "critical", "high", "medium"):
                events.record(
                    "web", f.category, category="finding", severity=f.severity,
                    detail=f.info, ref=f"{f.method} {f.path}".strip() or res.target,
                    payload={"parameter": f.parameter})
    except Exception:  # pylint: disable=broad-except
        pass


# ============================================================
# Relatórios (JSON 0600 + histórico + export TXT)
# ============================================================


def _ensure_reports_dir() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR


def result_to_dict(r: ScanResult) -> dict:
    return {
        "target": r.target,
        "profile": r.profile,
        "started_at": r.started_at,
        "elapsed_sec": r.elapsed_sec,
        "error": r.error,
        "findings": [
            {"category": f.category, "severity": f.severity, "method": f.method,
             "path": f.path, "info": f.info, "parameter": f.parameter}
            for f in r.findings
        ],
    }


def result_to_text(r: ScanResult) -> str:
    lines = [
        f"Vigia Web Scanner — {r.target}",
        f"Perfil: {r.profile} · {r.started_at} · {r.elapsed_sec:.0f}s",
        "=" * 56,
    ]
    if r.error:
        lines.append(f"Erro: {r.error}")
        return "\n".join(lines) + "\n"
    if not r.findings:
        lines.append("Nenhuma vulnerabilidade encontrada para este perfil.")
        return "\n".join(lines) + "\n"
    for f in r.findings:
        lines.append(f"\n[{f.severity.upper()}] {f.category}")
        loc = f"{f.method} {f.path}".strip()
        if loc:
            lines.append(f"  Em: {loc}"
                         + (f"  (param: {f.parameter})" if f.parameter else ""))
        if f.info:
            lines.append(f"  {f.info}")
    return "\n".join(lines) + "\n"


def save_report(result: ScanResult) -> Path | None:
    if not result.started_at:
        return None
    rd = _ensure_reports_dir()
    safe_ts = result.started_at.replace(":", "-").replace(".", "_")
    path = rd / f"web-{safe_ts}.json"
    return path if save_json_0600(path, result_to_dict(result)) else None


def list_recent_reports(limit: int = 20) -> list[dict]:
    if not REPORTS_DIR.is_dir():
        return []
    files = sorted(
        REPORTS_DIR.glob("web-*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    out: list[dict] = []
    for f in files[:limit]:
        data = load_json(f)
        if isinstance(data, dict):
            data["_file"] = str(f)
            out.append(data)
    return out
