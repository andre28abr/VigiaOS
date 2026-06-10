"""Backend do Vigia Network Scanner — descoberta de portas/serviços via nmap.

Reconhecimento ATIVO: conecta nas portas do alvo (≠ Recon, que é passivo).
Roda sem root por padrão (TCP connect, `-sT`), saída em XML (`-oX -`) que é
estruturada e estável — parseada com a stdlib (xml.etree).

Partes PURAS (testáveis sem nmap, sem GTK):
- `normalize_target` / `validate_target` — domínio, IP ou faixa CIDR.
- `build_scan_cmd(...)` — argv do nmap (lista, nunca shell).
- `parse_nmap_xml(...)` — XML do nmap → hosts/portas/serviços.

Parte que toca o sistema:
- `run_scan(...)` — roda via `vigia_common.proc.run` (nunca levanta) + relatório 0600.
"""

from __future__ import annotations

import ipaddress
import re
import shutil
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from vigia_common import proc
from vigia_common.state import load_json, save_json_0600

# ~/.local/share/vigia-netscan/scan-*.json
DATA_DIR = Path.home() / ".local" / "share" / "vigia-netscan"
REPORTS_DIR = DATA_DIR

# Faixa CIDR não pode ser gigante (evita varredura em massa acidental).
MAX_HOSTS = 1024


# ============================================================
# Perfis de varredura
# ============================================================


@dataclass(frozen=True)
class Profile:
    id: str
    label: str
    description: str
    args: tuple[str, ...]   # flags extras do nmap


PROFILES: list[Profile] = [
    Profile("rapida", "Rápida",
            "As 100 portas mais comuns, sem versão — alguns segundos.",
            ("-F",)),
    Profile("padrao", "Padrão",
            "1000 portas + detecção de serviço/versão. Recomendado.",
            ("-sV",)),
    Profile("completa", "Completa",
            "Todas as 65535 portas + versão. Lento (minutos).",
            ("-p-", "-sV")),
]
DEFAULT_PROFILE = "padrao"


# ============================================================
# Dataclasses de resultado
# ============================================================


@dataclass
class Port:
    port: int
    proto: str = "tcp"
    state: str = "open"
    service: str = ""
    product: str = ""
    version: str = ""

    def describe(self) -> str:
        """'OpenSSH 8.0' / 'ssh' / '' — o mais informativo disponível."""
        prod = " ".join(p for p in (self.product, self.version) if p).strip()
        return prod or self.service or ""


@dataclass
class Host:
    address: str
    hostname: str = ""
    state: str = ""
    ports: list[Port] = field(default_factory=list)


@dataclass
class ScanResult:
    target: str
    profile: str = ""
    hosts: list[Host] = field(default_factory=list)
    started_at: str = ""
    elapsed_sec: float = 0.0
    error: str = ""
    ran: bool = False        # True se o nmap rodou e devolveu XML

    @property
    def open_ports(self) -> int:
        return sum(len(h.ports) for h in self.hosts)

    @property
    def hosts_up(self) -> int:
        return sum(1 for h in self.hosts if h.ports or h.state == "up")


# ============================================================
# Disponibilidade
# ============================================================


def nmap_available() -> bool:
    return shutil.which("nmap") is not None


# ============================================================
# Validação / normalização do alvo (puro)
# ============================================================

_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))+$"
)


def normalize_target(t: str) -> str:
    """Tira esquema (http://) e espaços. Mantém '/' (faixa CIDR é válida)."""
    t = (t or "").strip()
    t = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://", "", t)
    return t.strip().rstrip(".")


def validate_target(t: str) -> bool:
    """True se `t` é um domínio, um IP (v4/v6) ou uma faixa CIDR."""
    t = normalize_target(t)
    if not t or any(c.isspace() for c in t):
        return False
    try:
        ipaddress.ip_network(t, strict=False)   # IP ou rede CIDR
        return True
    except ValueError:
        pass
    return "/" not in t and bool(_DOMAIN_RE.match(t.lower()))


def network_too_large(t: str) -> bool:
    """True se for uma faixa CIDR com mais de MAX_HOSTS endereços."""
    try:
        net = ipaddress.ip_network(normalize_target(t), strict=False)
    except ValueError:
        return False
    return net.num_addresses > MAX_HOSTS


# ============================================================
# Command builder (puro)
# ============================================================


def build_scan_cmd(target: str, profile_args: tuple[str, ...] | list[str]) -> list[str]:
    """Monta o argv do nmap (lista — nunca shell string).

    `-sT`  TCP connect (não precisa de root).
    `-Pn`  não faz ping (escaneia mesmo host que bloqueia ICMP).
    `--open` só mostra portas abertas.
    `-T4`  timing agressivo (mais rápido).
    `-oX -` saída XML no stdout (estruturada, parseável).
    """
    return [
        "nmap", "-sT", "-Pn", "--open", "-T4",
        *profile_args,
        "-oX", "-",
        target,
    ]


# ============================================================
# Parser do XML do nmap (puro)
# ============================================================


def parse_nmap_xml(xml_text: str) -> list[Host]:
    """Parseia a saída `-oX` do nmap em hosts/portas. Nunca levanta."""
    hosts: list[Host] = []
    try:
        root = ET.fromstring(xml_text or "")
    except ET.ParseError:
        return hosts

    for h in root.findall("host"):
        st = h.find("status")
        state = st.get("state", "") if st is not None else ""

        address = ""
        for a in h.findall("address"):
            if a.get("addrtype") in ("ipv4", "ipv6"):
                address = a.get("addr", "")
                break
        if not address:
            a = h.find("address")
            address = a.get("addr", "") if a is not None else ""

        hostname = ""
        hn = h.find("hostnames/hostname")
        if hn is not None:
            hostname = hn.get("name", "")

        ports: list[Port] = []
        for p in h.findall("ports/port"):
            pst = p.find("state")
            pstate = pst.get("state", "") if pst is not None else ""
            if pstate != "open":
                continue
            svc = p.find("service")
            try:
                portid = int(p.get("portid", "0"))
            except (TypeError, ValueError):
                portid = 0
            ports.append(Port(
                port=portid,
                proto=p.get("protocol", "tcp"),
                state=pstate,
                service=svc.get("name", "") if svc is not None else "",
                product=svc.get("product", "") if svc is not None else "",
                version=svc.get("version", "") if svc is not None else "",
            ))
        ports.sort(key=lambda x: x.port)
        if address or ports:
            hosts.append(Host(address, hostname, state, ports))
    return hosts


def _last_line(text: str) -> str:
    for line in reversed((text or "").splitlines()):
        s = line.strip()
        if s:
            return s[:200]
    return ""


# ============================================================
# Scan (toca o sistema via proc.run)
# ============================================================


def run_scan(
    target: str,
    profile_id: str = DEFAULT_PROFILE,
    timeout: int = 600,
) -> ScanResult:
    """Varre `target` com o perfil. Nunca levanta; erros vão em `.error`."""
    tgt = normalize_target(target)
    res = ScanResult(
        target=tgt,
        profile=profile_id,
        started_at=datetime.now().isoformat(timespec="seconds"),
    )
    if not validate_target(tgt):
        res.error = ("Alvo inválido. Use um domínio, IP ou faixa — ex.: "
                     "exemplo.com.br, 192.168.0.10 ou 192.168.0.0/24.")
        return res
    if network_too_large(tgt):
        res.error = f"Faixa grande demais (máx. {MAX_HOSTS} endereços)."
        return res
    if not nmap_available():
        res.error = "nmap não está instalado."
        return res

    prof = next((p for p in PROFILES if p.id == profile_id), None)
    args = prof.args if prof else ("-sV",)

    t0 = time.monotonic()
    rc, out, err = proc.run(build_scan_cmd(tgt, args), timeout=timeout)
    res.elapsed_sec = round(time.monotonic() - t0, 2)

    res.ran = "<nmaprun" in (out or "")
    if res.ran:
        res.hosts = parse_nmap_xml(out)
    else:
        res.error = _last_line(err) or _last_line(out) or (
            f"O nmap não retornou resultado (código {rc}).")

    save_report(res)
    return res


# ============================================================
# Relatórios (JSON 0600 + histórico)
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
        "hosts": [
            {
                "address": h.address,
                "hostname": h.hostname,
                "state": h.state,
                "ports": [
                    {"port": p.port, "proto": p.proto, "state": p.state,
                     "service": p.service, "product": p.product,
                     "version": p.version}
                    for p in h.ports
                ],
            }
            for h in r.hosts
        ],
    }


def save_report(result: ScanResult) -> Path | None:
    """Salva em ~/.local/share/vigia-netscan/scan-<ts>.json (0600)."""
    if not result.started_at:
        return None
    rd = _ensure_reports_dir()
    safe_ts = result.started_at.replace(":", "-").replace(".", "_")
    path = rd / f"scan-{safe_ts}.json"
    return path if save_json_0600(path, result_to_dict(result)) else None


def list_recent_reports(limit: int = 20) -> list[dict]:
    """Relatórios salvos, mais novos primeiro (descarta corrompidos)."""
    if not REPORTS_DIR.is_dir():
        return []
    files = sorted(
        REPORTS_DIR.glob("scan-*.json"),
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
