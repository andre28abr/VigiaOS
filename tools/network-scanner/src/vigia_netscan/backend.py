"""Backend nmap.

Operacoes:
- nmap_installed() -> bool
- scan_blocking(target, profile) -> ScanResult
- list_recent_scans() -> list[dict]

Reports salvos em ~/.local/share/vigia-netscan/ com mode 0600 (LGPD).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from .profiles import ScanProfile


HISTORY_DIR = Path.home() / ".local" / "share" / "vigia-netscan"


@dataclass
class Port:
    port: int
    protocol: str = "tcp"
    state: str = ""          # open|closed|filtered
    service: str = ""        # ex: "http"
    product: str = ""        # ex: "nginx"
    version: str = ""        # ex: "1.18.0"


@dataclass
class Host:
    address: str = ""
    hostname: str = ""
    status: str = ""         # up|down
    os_guess: str = ""
    ports: list[Port] = field(default_factory=list)


@dataclass
class ScanResult:
    target: str
    profile_id: str
    started_at: str = ""
    elapsed_sec: float = 0.0
    hosts: list[Host] = field(default_factory=list)
    raw_xml: str = ""
    error: str = ""


# ============================================================
# Sanity
# ============================================================


def nmap_installed() -> bool:
    return shutil.which("nmap") is not None


def validate_target(target: str) -> tuple[bool, str]:
    """Valida que target e' IP/hostname/CIDR razoavel.

    Aceita: 192.168.1.1, 10.0.0.0/24, scanme.nmap.org, fe80::1.
    Rejeita:
    - strings com espacos, ;, |, $ (injection)
    - strings comecando com '-' (flag injection: --script=evil.nse,
      -iL/etc/shadow, -oN/tmp/exec.sh, etc.)
    - strings vazias ou longas demais (>200 chars)

    CRITICAL: nao rejeitar '-' inicial permite ESCALATION para RCE em
    perfis com pkexec (stealth, aggressive). Ex: 'target=-iL/etc/shadow'
    faria nmap ler /etc/shadow como input list.
    """
    if not target or len(target) > 200:
        return False, "Target vazio ou muito longo."

    # CRITICAL: rejeitar prefixo '-' (flag injection no nmap).
    # Mesmo com -- separator no cmd, esse check e' defense-in-depth.
    if target.lstrip().startswith("-"):
        return False, (
            "Target nao pode comecar com '-' (interpretado como flag pelo "
            "nmap). Use o nome do host sem prefixo."
        )

    # Caracteres permitidos: letras, digitos, . - _ : / espaco para multi-target
    if not re.match(r"^[a-zA-Z0-9.\-_:/, ]+$", target):
        return False, "Target contem caracteres invalidos."

    # Rejeita targets multi onde QUALQUER um comeca com '-' (multi-target
    # com flag injection: 'host1,-iL/etc/shadow')
    for sub_target in re.split(r"[,\s]+", target):
        if sub_target and sub_target.startswith("-"):
            return False, f"Sub-target invalido (comeca com '-'): {sub_target}"

    return True, ""


def _run(cmd: list[str], timeout: int = 600) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 1, "", ""


# ============================================================
# Scan
# ============================================================


def scan_blocking(target: str, profile: ScanProfile, timeout: int = 600) -> ScanResult:
    """Roda nmap com perfil e retorna ScanResult parseado.

    Args:
        target: IP, hostname ou CIDR.
        profile: ScanProfile do catalogo.
        timeout: limite em segundos.
    """
    result = ScanResult(
        target=target,
        profile_id=profile.id,
        started_at=datetime.now().isoformat(timespec="seconds"),
    )

    if not nmap_installed():
        result.error = "nmap nao instalado. Instale com: rpm-ostree install nmap"
        return result

    ok, err = validate_target(target)
    if not ok:
        result.error = err
        return result

    base_cmd: list[str] = []
    if profile.needs_root:
        if shutil.which("pkexec") is None:
            result.error = "pkexec nao encontrado, mas perfil precisa root."
            return result
        base_cmd = ["pkexec", "nmap"]
    else:
        base_cmd = ["nmap"]

    # XML output para parsing robusto. Stats every 10s pra futuro streaming.
    # CRITICAL: '--' separator obriga nmap a interpretar `target` SEMPRE
    # como hostname, nunca como flag. Defense-in-depth alem de validate_target.
    cmd = base_cmd + profile.args + ["-oX", "-", "--", target]

    start = time.time()
    rc, out, err = _run(cmd, timeout=timeout)
    result.elapsed_sec = round(time.time() - start, 2)

    if rc in (126, 127):
        result.error = "Autenticacao cancelada."
        return result
    if not out:
        result.error = err.strip() or "nmap nao retornou output."
        return result

    result.raw_xml = out
    try:
        result.hosts = _parse_nmap_xml(out)
    except ET.ParseError as e:
        result.error = f"Falha ao parsear XML do nmap: {e}"
        return result

    if rc != 0 and not result.hosts:
        result.error = (err or "nmap retornou erro.").strip()[:500]
        return result

    _save_history(result)
    return result


def _parse_nmap_xml(xml_text: str) -> list[Host]:
    hosts: list[Host] = []
    root = ET.fromstring(xml_text)
    for host_el in root.findall("host"):
        host = Host()
        status_el = host_el.find("status")
        if status_el is not None:
            host.status = status_el.get("state", "")

        for addr_el in host_el.findall("address"):
            if addr_el.get("addrtype") in ("ipv4", "ipv6"):
                host.address = addr_el.get("addr", "")
                break

        hostnames = host_el.find("hostnames")
        if hostnames is not None:
            for hn in hostnames.findall("hostname"):
                if hn.get("name"):
                    host.hostname = hn.get("name", "")
                    break

        ports_el = host_el.find("ports")
        if ports_el is not None:
            for port_el in ports_el.findall("port"):
                p = Port(
                    port=int(port_el.get("portid", "0")),
                    protocol=port_el.get("protocol", "tcp"),
                )
                state_el = port_el.find("state")
                if state_el is not None:
                    p.state = state_el.get("state", "")
                svc_el = port_el.find("service")
                if svc_el is not None:
                    p.service = svc_el.get("name", "")
                    p.product = svc_el.get("product", "")
                    p.version = svc_el.get("version", "")
                host.ports.append(p)

        # OS guess (so com -A ou -O)
        os_el = host_el.find("os")
        if os_el is not None:
            best = os_el.find("osmatch")
            if best is not None:
                host.os_guess = best.get("name", "")

        hosts.append(host)
    return hosts


# ============================================================
# History
# ============================================================


def _ensure_history_dir() -> Path:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(HISTORY_DIR, 0o700)
    except OSError:
        pass
    return HISTORY_DIR


def _save_history(result: ScanResult) -> None:
    hd = _ensure_history_dir()
    safe_ts = result.started_at.replace(":", "-").replace(".", "_")
    path = hd / f"scan-{safe_ts}.json"
    data = {
        "target": result.target,
        "profile_id": result.profile_id,
        "started_at": result.started_at,
        "elapsed_sec": result.elapsed_sec,
        "hosts": [
            {
                "address": h.address,
                "hostname": h.hostname,
                "status": h.status,
                "os_guess": h.os_guess,
                "ports": [
                    {
                        "port": p.port,
                        "protocol": p.protocol,
                        "state": p.state,
                        "service": p.service,
                        "product": p.product,
                        "version": p.version,
                    }
                    for p in h.ports
                ],
            }
            for h in result.hosts
        ],
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.chmod(path, 0o600)
    except OSError:
        pass


def list_recent_scans(limit: int = 20) -> list[dict]:
    if not HISTORY_DIR.is_dir():
        return []
    files = sorted(HISTORY_DIR.glob("scan-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for f in files[:limit]:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            data["_file"] = str(f)
            out.append(data)
        except (OSError, json.JSONDecodeError):
            continue
    return out
