"""Operacoes SELinux invocadas via subprocess.

Read-only (getenforce, getsebool, sestatus) roda como user — qualquer um
pode ler. Operacoes que mudam estado (setenforce, setsebool) requerem root
e sao invocadas via pkexec, o que abre o dialogo grafico polkit do GNOME.
"""

from __future__ import annotations

import re
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
    description: str = ""

    @property
    def display_description(self) -> str:
        """Descricao para mostrar na UI. Fallback se nao houver."""
        if self.description:
            # Tentativa simples de traducao pt-BR para palavras comuns
            return _localize(self.description)
        return "Sem descricao disponivel (rode 'semanage boolean -l' para detalhes)"


# Pequeno dict de traducoes pt-BR para frases comuns que aparecem nas descricoes.
# Mantemos a frase original e SO substituimos as palavras iniciais quando bate.
_PT_HINTS: dict[str, str] = {
    "Allow ": "Permitir ",
    "Deny ": "Negar ",
    "Determine whether ": "Define se ",
    "Allows ": "Permite ",
    "Enable ": "Habilitar ",
}


def _localize(text: str) -> str:
    """Pequeno hint de traducao para descricoes (best-effort)."""
    for en, pt in _PT_HINTS.items():
        if text.startswith(en):
            return pt + text[len(en):]
    return text


def list_booleans() -> list[Boolean]:
    """Lista booleans SELinux com descricao se disponivel.

    Tenta primeiro `semanage boolean -l` (tem descricoes mas pode falhar
    em alguns ambientes). Fallback para `getsebool -a` (so name + value).
    """
    # Primeira tentativa: semanage tem descricoes
    semanage_result = _try_semanage_booleans()
    if semanage_result:
        return semanage_result

    # Fallback: getsebool sem descricoes
    return _getsebool_booleans()


def _try_semanage_booleans() -> list[Boolean]:
    """Parse output de 'semanage boolean -l'.

    Formato esperado (com colunas variaveis de espaco):
        SELinux boolean             State  Default Description
        abrt_anon_write             (off  ,  off)  Allow ABRT to write files in...
        abrt_handle_event           (off  ,  off)  Allow ABRT to run in abrt_h...
    """
    if shutil.which("semanage") is None:
        return []
    try:
        result = subprocess.run(
            ["semanage", "boolean", "-l"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return []
    if result.returncode != 0 or not result.stdout.strip():
        return []

    # Regex: <name> ( <current> , <default> ) <description>
    pattern = re.compile(
        r"^(\S+)\s+\(\s*(\S+?)\s*,\s*(\S+?)\s*\)\s*(.*)$"
    )
    booleans: list[Boolean] = []
    for line in result.stdout.splitlines():
        line = line.rstrip()
        if not line or line.startswith("SELinux boolean") or "----" in line:
            continue
        match = pattern.match(line)
        if not match:
            continue
        name, current, _default, description = match.groups()
        booleans.append(
            Boolean(
                name=name,
                value=current.lower() == "on",
                description=description.strip(),
            )
        )
    return booleans


def _getsebool_booleans() -> list[Boolean]:
    """Fallback: parseia 'getsebool -a' (sem descricoes)."""
    try:
        result = subprocess.run(
            ["getsebool", "-a"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return []

    booleans: list[Boolean] = []
    for line in result.stdout.splitlines():
        parts = line.split("-->", 1)
        if len(parts) != 2:
            continue
        booleans.append(
            Boolean(
                name=parts[0].strip(),
                value=parts[1].strip().lower() == "on",
                description="",
            )
        )
    return booleans


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
