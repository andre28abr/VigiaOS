"""Backend do Vigia Recon — OSINT passivo (reconhecimento de fontes abertas).

Wrapper do CLI `theHarvester`: dado um domínio autorizado, consulta fontes
públicas (transparência de certificados, DNS, buscadores) e devolve a superfície
externa do alvo — e-mails, subdomínios, IPs, URLs. **Passivo**: nunca toca nos
servidores do alvo, só lê o que já é público.

Partes PURAS (testáveis headless, sem `theHarvester` instalado):
- `normalize_domain` / `validate_domain` — saneia e valida o alvo.
- `build_harvester_cmd(...)` — monta o argv (lista, nunca shell — convenção do projeto).
- `parse_harvester_json(...)` — parser robusto da saída JSON do theHarvester.

Parte que toca o sistema:
- `run_recon(...)` — roda via `vigia_common.proc.run` (nunca levanta) + salva relatório 0600.

O theHarvester grava `<base>.json`/`<base>.xml` via `-f`; lemos o JSON e
extraímos `emails`, `hosts` ("host" ou "host:ip"), `ips`, `interesting_urls`.
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

# ~/.local/share/vigia-recon/recon-*.json
DATA_DIR = Path.home() / ".local" / "share" / "vigia-recon"
REPORTS_DIR = DATA_DIR


# ============================================================
# Fontes OSINT (passivas, sem chave de API) — curadas
# ============================================================


@dataclass(frozen=True)
class Source:
    """Uma fonte pública consultada pelo theHarvester."""

    id: str       # id da fonte no theHarvester (ex: "crtsh")
    label: str    # rótulo PT-BR
    note: str = ""


# Subconjunto estável que NÃO exige chave de API. (Fontes como shodan/github
# exigem key e ficam de fora do conjunto padrão.)
SOURCES: list[Source] = [
    Source("crtsh", "Certificados SSL (crt.sh)",
           "Subdomínios via transparência de certificados"),
    Source("hackertarget", "HackerTarget", "Hosts e DNS"),
    Source("rapiddns", "RapidDNS", "Subdomínios"),
    Source("anubis", "Anubis", "Subdomínios"),
    Source("otx", "AlienVault OTX", "Inteligência de ameaças"),
    Source("urlscan", "urlscan.io", "Subdomínios e URLs"),
    Source("duckduckgo", "DuckDuckGo", "Busca por e-mails e hosts"),
    Source("threatminer", "ThreatMiner", "Hosts e e-mails"),
    Source("bing", "Bing", "Busca por e-mails e hosts"),
]

# Padrão: fontes confiáveis e key-free que costumam responder bem.
DEFAULT_SOURCE_IDS = [
    "crtsh", "hackertarget", "rapiddns", "anubis", "otx", "urlscan", "duckduckgo",
]


@dataclass
class ReconResult:
    """Resultado de um recon: a superfície externa do domínio."""

    domain: str
    emails: list[str] = field(default_factory=list)
    hosts: list[str] = field(default_factory=list)   # subdomínios
    ips: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    started_at: str = ""
    elapsed_sec: float = 0.0
    error: str = ""
    ran: bool = False        # True se o theHarvester rodou e gravou o JSON

    @property
    def total(self) -> int:
        return len(self.emails) + len(self.hosts) + len(self.ips) + len(self.urls)


# ============================================================
# Sanity / disponibilidade
# ============================================================


def _harvester_bin() -> str | None:
    """Caminho do executável do theHarvester (o nome varia entre distros)."""
    for name in ("theHarvester", "theharvester", "theHarvester.py"):
        found = shutil.which(name)
        if found:
            return found
    return None


def theharvester_available() -> bool:
    return _harvester_bin() is not None


# ============================================================
# Validação / normalização do alvo (puro)
# ============================================================

# Domínio válido: rótulos alfanuméricos (com hífen no meio), pelo menos 1 ponto.
_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))+$"
)


def normalize_domain(domain: str) -> str:
    """Tira esquema (http://), caminho, porta e espaços — sobra só o domínio."""
    d = (domain or "").strip().lower()
    d = re.sub(r"^[a-z][a-z0-9+.\-]*://", "", d)   # remove http:// etc.
    d = d.split("/", 1)[0]                          # remove caminho
    d = d.split("@", 1)[-1]                          # remove user@ (caso colem e-mail)
    d = d.split(":", 1)[0]                           # remove :porta
    d = d.strip(". ")
    if d.startswith("www.") and d.count(".") >= 2:   # www.dominio.com -> dominio.com
        d = d[4:]
    return d


def validate_domain(domain: str) -> bool:
    """True se `domain` é um domínio simples válido (já normalizado ou não)."""
    d = normalize_domain(domain)
    return bool(_DOMAIN_RE.match(d))


# ============================================================
# Command builder (puro)
# ============================================================


def build_harvester_cmd(
    domain: str,
    source_ids: list[str],
    out_basename: Path | str,
    limit: int = 500,
) -> list[str]:
    """Monta o argv do `theHarvester` (lista — nunca shell string).

    `theHarvester -d DOMINIO -b fonte1,fonte2 -l LIMITE -f BASE`.
    `-f BASE` faz o theHarvester gravar `BASE.json` (e `.xml`) com o resultado.
    Segurança vem de passar argv em LISTA (sem shell); o domínio é validado antes.
    """
    binp = _harvester_bin() or "theHarvester"
    return [
        binp,
        "-d", domain,
        "-b", ",".join(source_ids) if source_ids else "crtsh",
        "-l", str(limit),
        "-f", str(out_basename),
    ]


# ============================================================
# Parser do JSON do theHarvester (puro)
# ============================================================


def _clean(items) -> list[str]:
    """Normaliza uma lista de strings: tira vazios, dedup (case-insensitive), ordena."""
    seen: set[str] = set()
    out: list[str] = []
    for it in items or []:
        if not isinstance(it, str):
            continue
        s = it.strip().strip(".")
        key = s.lower()
        if s and key not in seen:
            seen.add(key)
            out.append(s)
    return sorted(out, key=str.lower)


def parse_harvester_json(data, domain: str = "") -> ReconResult:
    """Extrai e-mails/hosts/ips/urls do JSON do theHarvester (robusto a variações).

    `hosts` pode vir como "sub.dominio.com" ou "sub.dominio.com:1.2.3.4" — neste
    caso separamos o IP. Chaves ausentes viram listas vazias; nunca levanta.
    """
    res = ReconResult(domain=domain)
    if not isinstance(data, dict):
        return res

    ips: list[str] = list(data.get("ips") or [])
    hosts_raw = data.get("hosts") or []
    parsed_hosts: list[str] = []
    for h in hosts_raw:
        if not isinstance(h, str):
            continue
        if ":" in h:                       # "host:ip"
            name, _, ip = h.partition(":")
            if name.strip():
                parsed_hosts.append(name.strip())
            if ip.strip():
                ips.append(ip.strip())
        else:
            parsed_hosts.append(h.strip())

    urls = data.get("interesting_urls") or data.get("urls") or []

    res.emails = _clean(data.get("emails"))
    res.hosts = _clean(parsed_hosts)
    res.ips = _clean(ips)
    res.urls = _clean(urls)
    return res


# ============================================================
# Run (toca o sistema via proc.run)
# ============================================================


def _read_harvester_json(base: Path):
    """Lê o JSON que o theHarvester gravou (tenta variações de nome de arquivo)."""
    candidates = [
        base.with_suffix(".json"),
        Path(str(base) + ".json"),
        base,
    ]
    for cand in candidates:
        try:
            if cand.is_file():
                return json.loads(cand.read_text(encoding="utf-8", errors="replace"))
        except (OSError, json.JSONDecodeError, ValueError):
            continue
    return None


def _short_error(out: str, err: str) -> str:
    """Última linha ÚTIL da saída do theHarvester (ignora a arte ASCII do banner)."""
    for stream in (err, out):
        for line in reversed((stream or "").splitlines()):
            s = line.strip()
            if not s or set(s) <= set("*_|/\\ .-"):
                continue
            if s.startswith("*") and s.endswith("*"):
                continue
            return s[:200]
    return ""


def run_recon(
    domain: str,
    source_ids: list[str] | None = None,
    limit: int = 500,
    timeout: int = 300,
) -> ReconResult:
    """Roda o recon passivo no `domain`. Nunca levanta; erros vão em `.error`."""
    dom = normalize_domain(domain)
    res = ReconResult(
        domain=dom,
        started_at=datetime.now().isoformat(timespec="seconds"),
    )
    res.sources = list(source_ids) if source_ids else list(DEFAULT_SOURCE_IDS)

    if not validate_domain(dom):
        res.error = "Domínio inválido. Informe só o domínio, ex: exemplo.com.br"
        return res
    if not theharvester_available():
        res.error = "theHarvester não está instalado."
        return res

    t0 = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="vigia-recon-") as td:
        base = Path(td) / "out"
        cmd = build_harvester_cmd(dom, res.sources, base, limit)
        rc, out, err = proc.run(cmd, timeout=timeout)
        data = _read_harvester_json(base)

    res.elapsed_sec = round(time.monotonic() - t0, 2)
    res.ran = data is not None

    if res.ran:
        parsed = parse_harvester_json(data, dom)
        res.emails, res.hosts = parsed.emails, parsed.hosts
        res.ips, res.urls = parsed.ips, parsed.urls
    else:
        # Não gravou o JSON → falha real (≠ "rodou e não achou nada").
        res.error = _short_error(out, err) or (
            f"O theHarvester não retornou dados (código {rc}). "
            "Tente de novo ou rode no terminal pra ver o erro.")

    save_report(res)
    return res


# ============================================================
# Relatórios (JSON 0600 + histórico) — padrão dos módulos Vigia
# ============================================================


def _ensure_reports_dir() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR


def result_to_dict(result: ReconResult) -> dict:
    return {
        "domain": result.domain,
        "started_at": result.started_at,
        "elapsed_sec": result.elapsed_sec,
        "sources": result.sources,
        "emails": result.emails,
        "hosts": result.hosts,
        "ips": result.ips,
        "urls": result.urls,
        "error": result.error,
    }


def save_report(result: ReconResult) -> Path | None:
    """Salva o resultado em ~/.local/share/vigia-recon/recon-<ts>.json (0600)."""
    if not result.started_at:
        return None
    rd = _ensure_reports_dir()
    safe_ts = result.started_at.replace(":", "-").replace(".", "_")
    path = rd / f"recon-{safe_ts}.json"
    return path if save_json_0600(path, result_to_dict(result)) else None


def list_recent_reports(limit: int = 20) -> list[dict]:
    """Relatórios salvos, mais novos primeiro (descarta corrompidos)."""
    if not REPORTS_DIR.is_dir():
        return []
    files = sorted(
        REPORTS_DIR.glob("recon-*.json"),
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
