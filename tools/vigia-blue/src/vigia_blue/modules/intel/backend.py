"""Backend do Vigia Intel — inteligência de ameaças local (offline-first).

Em vez de depender de rede e chaves de API, o foco do v0.1 é o que dá valor
**offline, no escritório**: manter uma **base local de IOCs** (indicadores de
comprometimento — IPs, domínios, URLs, hashes, e-mails maliciosos) e
**checar indicadores** contra ela. Ex.: pegue os IPs que o Vigia SIEM mostrou
como força-bruta/bloqueados e veja quais já são conhecidos como maliciosos.

Importa IOCs de listas em texto puro e de exports **OTX** (AlienVault) e **MISP**
(arquivos que o usuário baixou) — tudo sem chamar a rede.

Partes PURAS (testáveis headless, sem gi):
- `detect_type(s)` / `normalize(s)` — classifica e normaliza um indicador.
- `check(indicadores, iocs)` — casa indicadores com a base.
- `import_plain(texto)` / `parse_otx_pulse(json)` / `parse_misp_event(json)`.
Toca o disco só na base local (`load_iocs`/`save_iocs`, 0600).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from vigia_common.state import load_json, save_json_0600

DATA_DIR = Path.home() / ".local" / "share" / "vigia-intel"
STORE = DATA_DIR / "iocs.json"

IOC_TYPES = ("ip", "domain", "url", "hash", "email", "other")

_IPV4_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
_HASH_RE = re.compile(r"^[a-fA-F0-9]{32}$|^[a-fA-F0-9]{40}$|^[a-fA-F0-9]{64}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9-]{1,63}\.)+[a-z]{2,}$")


@dataclass
class IOC:
    type: str
    value: str
    source: str = "manual"
    note: str = ""
    added_at: str = ""


@dataclass
class Match:
    indicator: str        # o que o usuário checou (texto original)
    ioc: IOC              # o IOC da base que casou


# ============================================================
# Classificação / normalização (pura)
# ============================================================


def detect_type(s: str) -> tuple[str, str]:
    """Classifica o indicador e devolve (tipo, valor_normalizado).

    Tipos: ip, domain, url, hash, email, other. Valor vazio se entrada vazia.
    """
    s = (s or "").strip()
    if not s:
        return "other", ""
    low = s.lower()
    if _HASH_RE.match(s):
        return "hash", low
    if _IPV4_RE.match(s):
        return "ip", s
    if low.startswith(("http://", "https://")):
        return "url", low
    if _EMAIL_RE.match(low):
        return "email", low
    if _DOMAIN_RE.match(low):
        return "domain", low
    return "other", low


def normalize(s: str) -> tuple[str, str]:
    return detect_type(s)


def _url_host(url: str) -> str:
    m = re.match(r"https?://([^/:?#]+)", url.lower())
    return m.group(1) if m else ""


# ============================================================
# Checagem (pura) — o coração do módulo
# ============================================================


def check(indicators: list[str], iocs: list[IOC]) -> list[Match]:
    """Casa cada indicador contra a base local. Match por (tipo, valor)
    normalizados; URL também testa o host contra IOCs de domínio."""
    index: dict[tuple[str, str], IOC] = {(i.type, i.value): i for i in iocs}
    out: list[Match] = []
    for raw in indicators:
        t, v = normalize(raw)
        if not v:
            continue
        hit = index.get((t, v))
        if hit is None and t == "url":
            host = _url_host(v)
            if host:
                hit = index.get(("domain", host))
        if hit is not None:
            out.append(Match(indicator=(raw or "").strip(), ioc=hit))
    return out


# ============================================================
# Importação (pura) — texto puro, OTX, MISP
# ============================================================


def import_plain(text: str, source: str = "importado") -> list[IOC]:
    """Uma linha = um indicador (ignora vazias e comentários `#`). Dedupe."""
    out: list[IOC] = []
    seen: set[tuple[str, str]] = set()
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        t, v = normalize(line)
        if not v or (t, v) in seen:
            continue
        seen.add((t, v))
        out.append(IOC(type=t, value=v, source=source))
    return out


_OTX_TYPE = {
    "IPv4": "ip", "IPv6": "ip", "domain": "domain", "hostname": "domain",
    "URL": "url", "URI": "url", "FileHash-MD5": "hash", "FileHash-SHA1": "hash",
    "FileHash-SHA256": "hash", "email": "email",
}


def parse_otx_pulse(data: dict) -> list[IOC]:
    """Parseia um pulse do AlienVault OTX (`indicators[]`)."""
    out: list[IOC] = []
    if not isinstance(data, dict):
        return out
    inds = data.get("indicators", [])
    if not isinstance(inds, list):
        return out
    for ind in inds:
        if not isinstance(ind, dict):
            continue
        val = str(ind.get("indicator", "")).strip()
        if not val:
            continue
        t, v = normalize(val)
        out.append(IOC(type=t, value=v, source="OTX",
                       note=str(ind.get("description", "") or ind.get("type", ""))))
    return out


def parse_misp_event(data: dict) -> list[IOC]:
    """Parseia um evento MISP (`Event.Attribute[]`)."""
    out: list[IOC] = []
    if not isinstance(data, dict):
        return out
    event = data.get("Event", data)
    attrs = event.get("Attribute", []) if isinstance(event, dict) else []
    if not isinstance(attrs, list):
        return out
    for a in attrs:
        if not isinstance(a, dict):
            continue
        val = str(a.get("value", "")).strip()
        if not val:
            continue
        t, v = normalize(val)
        out.append(IOC(type=t, value=v, source="MISP",
                       note=str(a.get("type", ""))))
    return out


# ============================================================
# Base local (0600)
# ============================================================


def load_iocs() -> list[IOC]:
    data = load_json(STORE, [])
    out: list[IOC] = []
    if isinstance(data, list):
        for d in data:
            if isinstance(d, dict) and d.get("value"):
                out.append(IOC(
                    type=str(d.get("type", "other")),
                    value=str(d.get("value")),
                    source=str(d.get("source", "manual")),
                    note=str(d.get("note", "")),
                    added_at=str(d.get("added_at", "")),
                ))
    return out


def save_iocs(iocs: list[IOC]) -> bool:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = [{"type": i.type, "value": i.value, "source": i.source,
             "note": i.note, "added_at": i.added_at} for i in iocs]
    return save_json_0600(STORE, data)


def add_iocs(new_iocs: list[IOC]) -> int:
    """Mescla na base, dedupe por (tipo, valor). Retorna quantos foram novos."""
    cur = load_iocs()
    index = {(i.type, i.value) for i in cur}
    added = 0
    for i in new_iocs:
        if not i.value or (i.type, i.value) in index:
            continue
        if not i.added_at:
            i.added_at = datetime.now().isoformat(timespec="seconds")
        cur.append(i)
        index.add((i.type, i.value))
        added += 1
    if added:
        save_iocs(cur)
    return added


def remove_ioc(value: str) -> int:
    cur = load_iocs()
    new = [i for i in cur if i.value != value]
    if len(new) != len(cur):
        save_iocs(new)
    return len(cur) - len(new)


def stats(iocs: list[IOC] | None = None) -> dict[str, int]:
    iocs = load_iocs() if iocs is None else iocs
    out: dict[str, int] = {}
    for i in iocs:
        out[i.type] = out.get(i.type, 0) + 1
    out["total"] = len(iocs)
    return out
