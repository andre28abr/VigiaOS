"""Backend do Vigia Vuln Scanner — vulnerabilidades por templates (nuclei).

Aprofunda o que o Network Scanner descobriu: dado um alvo (URL/host autorizado),
o nuclei roda milhares de templates da comunidade (CVEs, exposições, configs
erradas) e reporta cada achado com severidade. Saída em JSONL (`-jsonl`),
parseada com a stdlib.

Partes PURAS (testáveis sem nuclei, sem GTK):
- `normalize_target` / `validate_target` — URL, domínio ou IP.
- `build_nuclei_cmd(...)` — argv do nuclei (lista, nunca shell).
- `parse_nuclei_jsonl(...)` — JSONL do nuclei → achados ordenados por severidade.

Parte que toca o sistema:
- `run_scan(...)` — roda via runner cancelável / proc.run + relatório 0600.
"""

from __future__ import annotations

import ipaddress
import json
import re
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from vigia_common import proc
from vigia_common.state import load_json, save_json_0600

from ...runner import ScanProcess

DATA_DIR = Path.home() / ".local" / "share" / "vigia-vuln"
REPORTS_DIR = DATA_DIR


# ============================================================
# Perfis (presets de tags/severidade do nuclei)
# ============================================================


@dataclass(frozen=True)
class Profile:
    id: str
    label: str
    description: str
    args: tuple[str, ...]


PROFILES: list[Profile] = [
    Profile("cves", "CVEs graves",
            "Vulnerabilidades conhecidas de severidade alta/crítica. Focado.",
            ("-tags", "cve", "-severity", "critical,high")),
    Profile("padrao", "Padrão",
            "CVEs + exposições + configurações erradas (médio pra cima).",
            ("-tags", "cve,exposure,misconfig",
             "-severity", "critical,high,medium")),
    Profile("exposicoes", "Exposições",
            "Painéis, logins padrão e arquivos/segredos expostos.",
            ("-tags", "exposure,exposed-panels,default-login")),
    Profile("tech", "Tecnologias",
            "Identifica tecnologias e versões (sem explorar).",
            ("-tags", "tech")),
    Profile("completa", "Completa",
            "Todos os templates. Bem mais lento (minutos).",
            ()),
]
DEFAULT_PROFILE = "cves"

# ordem/severidades (pior primeiro)
SEVERITIES = ["critical", "high", "medium", "low", "info", "unknown"]
_SEV_ORDER = {s: i for i, s in enumerate(SEVERITIES)}


# ============================================================
# Dataclasses de resultado
# ============================================================


@dataclass
class Finding:
    template_id: str
    name: str
    severity: str = "unknown"
    tags: list[str] = field(default_factory=list)
    description: str = ""
    matched_at: str = ""
    host: str = ""


@dataclass
class ScanResult:
    target: str
    profile: str = ""
    findings: list[Finding] = field(default_factory=list)
    started_at: str = ""
    elapsed_sec: float = 0.0
    error: str = ""
    ran: bool = False
    raw: str = ""        # JSONL cru (pra exportar) — não vai no JSON salvo

    @property
    def total(self) -> int:
        return len(self.findings)


# ============================================================
# Disponibilidade / validação
# ============================================================


def nuclei_available() -> bool:
    return shutil.which("nuclei") is not None


_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))+$"
)
_URL_RE = re.compile(r"^https?://[^\s/$.?#][^\s]*$", re.IGNORECASE)


def normalize_target(t: str) -> str:
    return (t or "").strip()


def validate_target(t: str) -> bool:
    """True se `t` é uma URL (http/https), um domínio ou um IP."""
    t = normalize_target(t)
    if not t or any(c.isspace() for c in t):
        return False
    if _URL_RE.match(t):
        return True
    host = t.split("/", 1)[0].split(":", 1)[0]
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        pass
    return bool(_DOMAIN_RE.match(host.lower()))


# ============================================================
# Command builder (puro)
# ============================================================


def build_nuclei_cmd(target: str, profile_args: tuple[str, ...] | list[str]) -> list[str]:
    """Monta o argv do nuclei (lista — nunca shell string).

    `-jsonl` saída em JSON Lines; `-silent` só achados (sem banner/progresso);
    `-nc` sem cor; `-disable-update-check` não tenta atualizar na hora.
    """
    return [
        "nuclei",
        "-target", target,
        "-jsonl", "-silent", "-nc", "-disable-update-check",
        *profile_args,
    ]


# ============================================================
# Parser do JSONL do nuclei (puro)
# ============================================================


def parse_nuclei_jsonl(text: str) -> list[Finding]:
    """Parseia a saída `-jsonl` do nuclei (1 achado por linha). Nunca levanta."""
    findings: list[Finding] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        info = obj.get("info") if isinstance(obj.get("info"), dict) else {}
        tags = info.get("tags")
        if not isinstance(tags, list):
            tags = [t.strip() for t in str(tags).split(",")] if tags else []
        findings.append(Finding(
            template_id=str(obj.get("template-id") or obj.get("templateID") or ""),
            name=str(info.get("name") or "").strip(),
            severity=str(info.get("severity") or "unknown").strip().lower(),
            tags=[str(t) for t in tags],
            description=str(info.get("description") or "").strip(),
            matched_at=str(obj.get("matched-at") or obj.get("matched") or ""),
            host=str(obj.get("host") or ""),
        ))
    findings.sort(key=lambda f: (_SEV_ORDER.get(f.severity, 99), f.name.lower()))
    return findings


def counts_by_severity(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    return counts


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
    """Roda o nuclei no `target`. Nunca levanta; erros vão em `.error`."""
    tgt = normalize_target(target)
    res = ScanResult(
        target=tgt,
        profile=profile_id,
        started_at=datetime.now().isoformat(timespec="seconds"),
    )
    if not validate_target(tgt):
        res.error = ("Alvo inválido. Use uma URL ou domínio — ex.: "
                     "https://exemplo.com.br ou exemplo.com.br.")
        return res
    if not nuclei_available():
        res.error = "nuclei não está instalado."
        return res

    prof = next((p for p in PROFILES if p.id == profile_id), None)
    args = prof.args if prof else ()

    runner = handle.run if handle is not None else proc.run
    t0 = time.monotonic()
    rc, out, err = runner(build_nuclei_cmd(tgt, args), timeout=timeout)
    res.elapsed_sec = round(time.monotonic() - t0, 2)

    res.raw = out
    res.findings = parse_nuclei_jsonl(out)
    # nuclei sai 0 mesmo sem achados; rc!=0 sem achados = erro real.
    res.ran = rc == 0 or bool(res.findings)
    if not res.ran:
        res.error = _last_line(err) or _last_line(out) or (
            f"O nuclei não concluiu (código {rc}).")

    save_report(res)
    return res


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
            {"template_id": f.template_id, "name": f.name, "severity": f.severity,
             "tags": f.tags, "description": f.description,
             "matched_at": f.matched_at, "host": f.host}
            for f in r.findings
        ],
    }


def result_to_text(r: ScanResult) -> str:
    lines = [
        f"Vigia Vuln Scanner — {r.target}",
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
        lines.append(f"\n[{f.severity.upper()}] {f.name}  ({f.template_id})")
        if f.matched_at:
            lines.append(f"  Em: {f.matched_at}")
        if f.description:
            lines.append(f"  {f.description}")
    return "\n".join(lines) + "\n"


def save_report(result: ScanResult) -> Path | None:
    if not result.started_at:
        return None
    rd = _ensure_reports_dir()
    safe_ts = result.started_at.replace(":", "-").replace(".", "_")
    path = rd / f"vuln-{safe_ts}.json"
    return path if save_json_0600(path, result_to_dict(result)) else None


def list_recent_reports(limit: int = 20) -> list[dict]:
    if not REPORTS_DIR.is_dir():
        return []
    files = sorted(
        REPORTS_DIR.glob("vuln-*.json"),
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
