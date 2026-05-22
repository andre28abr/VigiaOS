"""Operacoes firewalld via firewall-cmd.

Read-only (--state, --get-default-zone, --list-services, etc.) roda como user.
Write ops usam pkexec para elevar via polkit. Write sempre faz
--permanent + --reload para persistir e aplicar.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


# ============================================================================
# Helpers
# ============================================================================

def _fw_cmd(*args: str, timeout: int = 10) -> tuple[int, str, str]:
    """Roda firewall-cmd e retorna (exit, stdout, stderr) sem levantar exception."""
    try:
        result = subprocess.run(
            ["firewall-cmd"] + list(args),
            capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return -1, "", ""


def _pkexec_fw(*args: str, timeout: int = 30) -> None:
    """Roda pkexec firewall-cmd ARGS. Raise RuntimeError em falha."""
    if shutil.which("pkexec") is None:
        raise RuntimeError("pkexec nao encontrado. Instale polkit.")
    result = subprocess.run(
        ["pkexec", "firewall-cmd"] + list(args),
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout).strip()
        if "Request dismissed" in stderr or result.returncode == 126:
            raise RuntimeError("Autenticacao cancelada pelo usuario.")
        raise RuntimeError(f"firewall-cmd {' '.join(args)} falhou: {stderr}")


def _reload() -> None:
    """Reload do firewalld para aplicar mudancas permanent."""
    _pkexec_fw("--reload")


# ============================================================================
# Availability
# ============================================================================

def is_firewalld_available() -> bool:
    """firewalld instalado no sistema?"""
    return shutil.which("firewall-cmd") is not None


# ============================================================================
# Status / daemon
# ============================================================================

def is_running() -> bool:
    """firewalld daemon esta rodando?"""
    if not is_firewalld_available():
        return False
    rc, out, _ = _fw_cmd("--state")
    return rc == 0 and out == "running"


def start_firewalld() -> None:
    _pkexec_systemctl("start", "firewalld")


def stop_firewalld() -> None:
    _pkexec_systemctl("stop", "firewalld")


def _pkexec_systemctl(action: str, unit: str) -> None:
    if shutil.which("pkexec") is None:
        raise RuntimeError("pkexec nao encontrado.")
    result = subprocess.run(
        ["pkexec", "systemctl", action, "--now", f"{unit}.service"]
        if action in ("enable", "disable")
        else ["pkexec", "systemctl", action, f"{unit}.service"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout).strip()
        if "Request dismissed" in stderr or result.returncode == 126:
            raise RuntimeError("Autenticacao cancelada pelo usuario.")
        raise RuntimeError(f"systemctl {action} {unit} falhou: {stderr}")


# ============================================================================
# Zones
# ============================================================================

def get_default_zone() -> str:
    rc, out, _ = _fw_cmd("--get-default-zone")
    return out if rc == 0 else "unknown"


def set_default_zone(zone: str) -> None:
    _pkexec_fw("--set-default-zone=" + zone)


def list_zones() -> list[str]:
    rc, out, _ = _fw_cmd("--get-zones")
    if rc != 0:
        return []
    return out.split()


@dataclass
class ActiveZone:
    name: str
    interfaces: list[str]
    sources: list[str]


def get_active_zones() -> list[ActiveZone]:
    """Parse --get-active-zones output. Formato:
        zone_name
          interfaces: eth0 wlan0
          sources: 10.0.0.0/24
    """
    rc, out, _ = _fw_cmd("--get-active-zones")
    if rc != 0 or not out:
        return []
    zones: list[ActiveZone] = []
    current: ActiveZone | None = None
    for line in out.splitlines():
        if not line.startswith(" "):
            # Inicio de nova zona
            current = ActiveZone(name=line.strip(), interfaces=[], sources=[])
            zones.append(current)
        elif current is not None:
            line = line.strip()
            if line.startswith("interfaces:"):
                current.interfaces = line.split(":", 1)[1].strip().split()
            elif line.startswith("sources:"):
                current.sources = line.split(":", 1)[1].strip().split()
    return zones


# ============================================================================
# Services in a zone
# ============================================================================

def list_zone_services(zone: str) -> list[str]:
    """Services atualmente permitidos na zona."""
    rc, out, _ = _fw_cmd(f"--zone={zone}", "--list-services")
    if rc != 0 or not out:
        return []
    return out.split()


def add_zone_service(zone: str, service: str) -> None:
    _pkexec_fw("--permanent", f"--zone={zone}", f"--add-service={service}")
    _reload()


def remove_zone_service(zone: str, service: str) -> None:
    _pkexec_fw("--permanent", f"--zone={zone}", f"--remove-service={service}")
    _reload()


def list_available_services() -> list[str]:
    """Lista de TODOS os services definidos no firewalld (não so' os habilitados)."""
    rc, out, _ = _fw_cmd("--get-services")
    if rc != 0 or not out:
        return []
    return sorted(out.split())


# ============================================================================
# Ports in a zone
# ============================================================================

@dataclass
class PortRule:
    port: str        # ex: "8080" ou "8000-8010"
    protocol: str    # "tcp" ou "udp"

    def to_arg(self) -> str:
        return f"{self.port}/{self.protocol}"


def list_zone_ports(zone: str) -> list[PortRule]:
    """Porta customizadas permitidas na zona."""
    rc, out, _ = _fw_cmd(f"--zone={zone}", "--list-ports")
    if rc != 0 or not out:
        return []
    rules: list[PortRule] = []
    for token in out.split():
        if "/" not in token:
            continue
        port, proto = token.split("/", 1)
        rules.append(PortRule(port=port, protocol=proto))
    return rules


def add_zone_port(zone: str, port: str, protocol: str) -> None:
    if protocol not in ("tcp", "udp"):
        raise ValueError(f"Protocolo invalido: {protocol}")
    if not port.replace("-", "").isdigit():
        raise ValueError(f"Porta invalida: {port}")
    _pkexec_fw("--permanent", f"--zone={zone}", f"--add-port={port}/{protocol}")
    _reload()


def remove_zone_port(zone: str, port: str, protocol: str) -> None:
    _pkexec_fw("--permanent", f"--zone={zone}", f"--remove-port={port}/{protocol}")
    _reload()
