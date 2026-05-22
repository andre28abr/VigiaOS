"""Operacoes SELinux invocadas via subprocess.

Read-only (getenforce, getsebool, sestatus) roda como user — qualquer um
pode ler. Operacoes que mudam estado (setenforce, setsebool) requerem root
e sao invocadas via pkexec, o que abre o dialogo grafico polkit do GNOME.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


# ============================================================================
# Status
# ============================================================================

def get_mode() -> str:
    """Retorna 'Enforcing', 'Permissive' ou 'Disabled'."""
    try:
        result = subprocess.run(
            ["getenforce"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return "Unknown"


def get_policy_type() -> str:
    """Retorna o nome da policy ativa (ex: 'targeted')."""
    try:
        result = subprocess.run(
            ["sestatus"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.splitlines():
            if "Loaded policy name:" in line:
                return line.split(":", 1)[1].strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return "Unknown"


def get_policy_version() -> str:
    try:
        result = subprocess.run(
            ["sestatus"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.splitlines():
            if "Policy version:" in line:
                return line.split(":", 1)[1].strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return "?"


def set_mode_enforcing(enforcing: bool) -> None:
    """Muda modo runtime (NAO persiste no boot — para isso seria preciso
    editar /etc/selinux/config + reboot). Usa pkexec para auth admin.
    """
    if shutil.which("pkexec") is None:
        raise RuntimeError("pkexec nao encontrado. Instale 'polkit'.")
    val = "1" if enforcing else "0"
    result = subprocess.run(
        ["pkexec", "setenforce", val],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        if "Request dismissed" in stderr or result.returncode == 126:
            raise RuntimeError("Autenticacao cancelada pelo usuario.")
        raise RuntimeError(f"setenforce {val} falhou: {stderr}")


# ============================================================================
# Booleans
# ============================================================================

@dataclass
class Boolean:
    name: str
    value: bool


def list_booleans() -> list[Boolean]:
    """Parseia output de `getsebool -a`. Funciona como user (sem root).

    Formato de cada linha: 'boolean_name --> on'  ou  'boolean_name --> off'
    """
    try:
        result = subprocess.run(
            ["getsebool", "-a"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return []

    out: list[Boolean] = []
    for line in result.stdout.splitlines():
        parts = line.split("-->", 1)
        if len(parts) != 2:
            continue
        name = parts[0].strip()
        value = parts[1].strip().lower() == "on"
        out.append(Boolean(name=name, value=value))
    return out


def set_boolean(name: str, value: bool, persistent: bool = True) -> None:
    """Muda valor de um SELinux boolean.

    persistent=True (default) usa -P para persistir no boot.
    Sempre usa pkexec para auth admin.
    """
    if shutil.which("pkexec") is None:
        raise RuntimeError("pkexec nao encontrado. Instale 'polkit'.")
    args = ["pkexec", "setsebool"]
    if persistent:
        args.append("-P")
    args.extend([name, "on" if value else "off"])
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        if "Request dismissed" in stderr or result.returncode == 126:
            raise RuntimeError("Autenticacao cancelada pelo usuario.")
        raise RuntimeError(f"setsebool {name} falhou: {stderr}")


# ============================================================================
# Availability
# ============================================================================

def is_selinux_available() -> bool:
    """SELinux esta instalado e tem comandos minimos disponiveis?"""
    return (
        shutil.which("getenforce") is not None
        and shutil.which("getsebool") is not None
    )
