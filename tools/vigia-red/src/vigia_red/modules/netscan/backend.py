"""Backend do Vigia Network Scanner — descoberta de portas/serviços via nmap.

Reconhecimento ATIVO: conecta nas portas do alvo (≠ Recon, que é passivo).
Por padrão roda sem root (TCP connect, `-sT`); o "modo admin" (pkexec) libera
SYN (`-sS`), UDP (`-sU`) e detecção de SO (`-O`/`-A`). Saída em XML (`-oX -`),
parseada com a stdlib.

Partes PURAS (testáveis sem nmap, sem GTK):
- `normalize_target` / `validate_target` / `network_too_large` — alvo.
- `validate_ports` — lista/faixa de portas custom.
- `build_scan_cmd(...)` — argv do nmap (lista; pkexec na frente se elevado).
- `parse_nmap_xml(...)` — XML → hosts/portas/serviços/SO/scripts.

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
    port_args: tuple[str, ...] = ()    # seleção de portas (-F, --top-ports N, -p X, -p-)
    scan_args: tuple[str, ...] = ()    # técnica/versão (-sV, -sS, -sU, -A, -sn)
    needs_root: bool = False           # precisa do modo admin (pkexec)


PROFILES: list[Profile] = [
    Profile("top", "Top serviços",
            "As 20 portas mais comuns + versão — relâmpago.",
            ("--top-ports", "20"), ("-sV",)),
    Profile("rapida", "Rápida",
            "As 100 portas mais comuns (sem versão).",
            ("-F",), ()),
    Profile("padrao", "Padrão",
            "1000 portas + detecção de serviço/versão. Recomendado.",
            (), ("-sV",)),
    Profile("web", "Web",
            "Portas de site (80/443/8080/8443…) + versão.",
            ("-p", "80,443,8080,8443,8000,3000,5000"), ("-sV",)),
    Profile("completa", "Completa",
            "Todas as 65535 portas + versão. Lento (minutos).",
            ("-p-",), ("-sV",)),
    Profile("pingsweep", "Descoberta de hosts",
            "Quem está vivo numa faixa de rede (sem varrer portas).",
            (), ("-sn",)),
    Profile("furtiva", "Furtiva / SYN — admin",
            "SYN scan: mais rápido e discreto. Precisa do modo admin.",
            (), ("-sS", "-sV"), needs_root=True),
    Profile("udp", "UDP comum — admin",
            "50 portas UDP comuns (DNS/SNMP/NTP…). Precisa do modo admin.",
            ("--top-ports", "50"), ("-sU",), needs_root=True),
    Profile("agressiva", "Agressiva — admin",
            "Versão + Sistema Operacional + scripts + traceroute. Precisa de admin.",
            (), ("-A",), needs_root=True),
]
DEFAULT_PROFILE = "padrao"


@dataclass(frozen=True)
class ScriptSet:
    id: str
    label: str
    description: str
    value: str       # valor do --script (vazio = nenhum)


SCRIPTS: list[ScriptSet] = [
    ScriptSet("none", "Nenhum", "Sem scripts NSE.", ""),
    ScriptSet("default", "Padrão (seguros)",
              "Banners e informações seguras (-sC).", "default"),
    ScriptSet("vuln", "Vulnerabilidades",
              "Procura vulnerabilidades conhecidas (mais lento e intrusivo).",
              "vuln"),
    ScriptSet("web", "Web",
              "Enumeração de serviços web (títulos, cabeçalhos, diretórios).",
              "http-enum,http-title,http-headers"),
]
DEFAULT_SCRIPT = "none"


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
    scripts: list[str] = field(default_factory=list)   # "id: saída"

    def describe(self) -> str:
        prod = " ".join(p for p in (self.product, self.version) if p).strip()
        return prod or self.service or ""


@dataclass
class Host:
    address: str
    hostname: str = ""
    state: str = ""
    os: str = ""
    ports: list[Port] = field(default_factory=list)


@dataclass
class ScanResult:
    target: str
    profile: str = ""
    hosts: list[Host] = field(default_factory=list)
    started_at: str = ""
    elapsed_sec: float = 0.0
    error: str = ""
    ran: bool = False
    raw_xml: str = ""        # XML cru do nmap (pra exportar) — não vai no JSON

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
# Validação do alvo / portas (puro)
# ============================================================

_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))+$"
)
_PORTS_RE = re.compile(r"^\d{1,5}(-\d{1,5})?(,\d{1,5}(-\d{1,5})?)*$")


def normalize_target(t: str) -> str:
    t = (t or "").strip()
    t = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://", "", t)
    return t.strip().rstrip(".")


def validate_target(t: str) -> bool:
    t = normalize_target(t)
    if not t or any(c.isspace() for c in t):
        return False
    try:
        ipaddress.ip_network(t, strict=False)
        return True
    except ValueError:
        pass
    return "/" not in t and bool(_DOMAIN_RE.match(t.lower()))


def network_too_large(t: str) -> bool:
    try:
        net = ipaddress.ip_network(normalize_target(t), strict=False)
    except ValueError:
        return False
    return net.num_addresses > MAX_HOSTS


def validate_ports(ports: str) -> bool:
    """True se `ports` é vazio (usa o perfil) ou uma lista/faixa válida 1-65535."""
    p = (ports or "").strip()
    if not p:
        return True
    if not _PORTS_RE.match(p):
        return False
    for chunk in p.split(","):
        for n in chunk.split("-"):
            if not (1 <= int(n) <= 65535):
                return False
    return True


# ============================================================
# Command builder (puro)
# ============================================================


def build_scan_cmd(
    target: str,
    profile: Profile,
    *,
    elevated: bool = False,
    ports: str = "",
    scripts: str = "",
) -> list[str]:
    """Monta o argv do nmap (lista — nunca shell). `pkexec` na frente se elevado.

    - `-sn` (ping sweep): descoberta de hosts, sem portas.
    - sem admin: força `-sT` (TCP connect, sem root) e remove técnicas root-only.
    - com admin: respeita a técnica do perfil (SYN/UDP/-A); sem ela, o nmap como
      root usa SYN por padrão.
    """
    if "-sn" in profile.scan_args:
        cmd = ["nmap", "-sn", "-T4", "-oX", "-", target]
        return (["pkexec"] + cmd) if elevated else cmd

    cmd = ["nmap", "-Pn", "--open", "-T4", "-oX", "-"]
    scan = list(profile.scan_args)
    if not elevated:
        scan = [a for a in scan if a not in ("-sS", "-sU", "-O", "-A")]
        cmd.append("-sT")
    cmd += scan
    cmd += (["-p", ports.strip()] if ports.strip() else list(profile.port_args))
    if scripts:
        cmd += ["--script", scripts]
    cmd.append(target)
    return (["pkexec"] + cmd) if elevated else cmd


# ============================================================
# Parser do XML do nmap (puro)
# ============================================================


def parse_nmap_xml(xml_text: str) -> list[Host]:
    """Parseia a saída `-oX` do nmap em hosts/portas/SO/scripts. Nunca levanta."""
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

        osmatch = h.find("os/osmatch")
        osname = osmatch.get("name", "") if osmatch is not None else ""

        ports: list[Port] = []
        for p in h.findall("ports/port"):
            pst = p.find("state")
            if (pst.get("state", "") if pst is not None else "") != "open":
                continue
            svc = p.find("service")
            try:
                portid = int(p.get("portid", "0"))
            except (TypeError, ValueError):
                portid = 0
            scripts: list[str] = []
            for s in p.findall("script"):
                sid = s.get("id", "")
                out = " ".join((s.get("output", "") or "").split())
                if sid:
                    scripts.append(f"{sid}: {out}"[:300] if out else sid)
            ports.append(Port(
                port=portid,
                proto=p.get("protocol", "tcp"),
                state="open",
                service=svc.get("name", "") if svc is not None else "",
                product=svc.get("product", "") if svc is not None else "",
                version=svc.get("version", "") if svc is not None else "",
                scripts=scripts,
            ))
        ports.sort(key=lambda x: x.port)
        if address or ports:
            hosts.append(Host(address, hostname, state, osname, ports))
    return hosts


def _last_line(text: str) -> str:
    for line in reversed((text or "").splitlines()):
        s = line.strip()
        if s:
            return s[:200]
    return ""


# ============================================================
# Execução cancelável (pra "Cancelar varredura")
# ============================================================


class ScanProcess:
    """Roda o nmap de forma cancelável — `cancel()` encerra o processo."""

    def __init__(self) -> None:
        self._proc = None
        self.cancelled = False

    def run(self, cmd: list[str], timeout: int = 600):
        import subprocess
        if self.cancelled:
            return 1, "", ""
        try:
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except (OSError, ValueError):
            return 1, "", ""
        try:
            out, err = self._proc.communicate(timeout=timeout)
            return (self._proc.returncode or 0), out, err
        except subprocess.TimeoutExpired:
            self._terminate()
            return 1, "", "tempo esgotado"
        except Exception:  # pylint: disable=broad-except
            return 1, "", ""

    def cancel(self) -> None:
        self.cancelled = True
        self._terminate()

    def _terminate(self) -> None:
        p = self._proc
        if p is None:
            return
        try:
            p.terminate()
            try:
                p.wait(timeout=3)
            except Exception:  # pylint: disable=broad-except
                p.kill()
        except Exception:  # pylint: disable=broad-except
            pass


# ============================================================
# Scan (toca o sistema via proc.run)
# ============================================================


def run_scan(
    target: str,
    profile_id: str = DEFAULT_PROFILE,
    *,
    elevated: bool = False,
    ports: str = "",
    scripts: str = "",
    timeout: int = 600,
    handle: ScanProcess | None = None,
) -> ScanResult:
    """Varre `target`. Nunca levanta; erros vão em `.error`. Se `handle` for
    passado, a varredura é cancelável (`handle.cancel()`)."""
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
    if not validate_ports(ports):
        res.error = "Portas inválidas. Use ex.: 80,443,8000-8100."
        return res
    if not nmap_available():
        res.error = "nmap não está instalado."
        return res

    prof = next((p for p in PROFILES if p.id == profile_id), None)
    if prof is None:
        prof = next(p for p in PROFILES if p.id == DEFAULT_PROFILE)
    if prof.needs_root and not elevated:
        res.error = ("Esse perfil precisa do Modo admin — ligue-o acima e "
                     "tente de novo.")
        return res

    runner = handle.run if handle is not None else proc.run
    t0 = time.monotonic()
    rc, out, err = runner(
        build_scan_cmd(tgt, prof, elevated=elevated, ports=ports, scripts=scripts),
        timeout=timeout)
    res.elapsed_sec = round(time.monotonic() - t0, 2)

    res.ran = "<nmaprun" in (out or "")
    if res.ran:
        res.raw_xml = out
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
                "os": h.os,
                "ports": [
                    {"port": p.port, "proto": p.proto, "state": p.state,
                     "service": p.service, "product": p.product,
                     "version": p.version, "scripts": p.scripts}
                    for p in h.ports
                ],
            }
            for h in r.hosts
        ],
    }


def result_to_text(r: ScanResult) -> str:
    """Relatório legível (TXT) — pra exportar/anexar."""
    lines = [
        f"Vigia Network Scanner — {r.target}",
        f"Perfil: {r.profile} · {r.started_at} · {r.elapsed_sec:.0f}s",
        "=" * 56,
    ]
    if r.error:
        lines.append(f"Erro: {r.error}")
        return "\n".join(lines) + "\n"
    for h in r.hosts:
        title = h.hostname or h.address
        extra = f" ({h.address})" if h.hostname and h.address else ""
        lines.append(f"\nHost: {title}{extra}" + (f"  [SO: {h.os}]" if h.os else ""))
        if not h.ports:
            lines.append("  (sem portas abertas)")
        for p in h.ports:
            lines.append(f"  {p.port}/{p.proto}  {p.service}  {p.describe()}".rstrip())
            for s in p.scripts:
                lines.append(f"      ↳ {s}")
    return "\n".join(lines) + "\n"


def save_report(result: ScanResult) -> Path | None:
    """Salva em ~/.local/share/vigia-netscan/scan-<ts>.json (0600)."""
    if not result.started_at:
        return None
    rd = _ensure_reports_dir()
    safe_ts = result.started_at.replace(":", "-").replace(".", "_")
    path = rd / f"scan-{safe_ts}.json"
    return path if save_json_0600(path, result_to_dict(result)) else None


def list_recent_reports(limit: int = 20) -> list[dict]:
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


# ============================================================
# Preferências (perfil padrão favorito)
# ============================================================

PREFS_FILE = Path.home() / ".config" / "vigia-red" / "netscan.json"


def load_prefs() -> dict:
    """Preferências salvas (perfil/script/portas/admin padrão). {} se não houver."""
    data = load_json(PREFS_FILE)
    return data if isinstance(data, dict) else {}


def save_prefs(profile: str = "", script: str = "", ports: str = "",
               elevated: bool = False) -> bool:
    """Salva as opções atuais como padrão (0600)."""
    return save_json_0600(PREFS_FILE, {
        "profile": profile, "script": script,
        "ports": ports, "elevated": bool(elevated),
    })
