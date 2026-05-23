"""Backend rpm-ostree.

Operacoes:
- is_package_installed(pkg) -> bool (via `rpm -q`)
- rpm_ostree_status() -> dict (parseia `rpm-ostree status --json`)
- pending_changes() -> dict com 'added', 'removed', 'has_pending'
- install_packages_blocking(pkgs) -> (success, output)
- uninstall_packages_blocking(pkgs) -> (success, output)
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class PendingChanges:
    has_pending: bool = False
    pending_added: list[str] = None  # type: ignore[assignment]
    pending_removed: list[str] = None  # type: ignore[assignment]
    current_layered: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.pending_added is None:
            self.pending_added = []
        if self.pending_removed is None:
            self.pending_removed = []
        if self.current_layered is None:
            self.current_layered = []


# ============================================================
# Sanity
# ============================================================


def rpm_available() -> bool:
    return shutil.which("rpm") is not None


def rpm_ostree_available() -> bool:
    return shutil.which("rpm-ostree") is not None


# ============================================================
# Status (pacotes layered e pending changes)
# ============================================================


def is_package_installed(pkg: str) -> bool:
    """Verifica via `rpm -q <pkg>` (funciona para base e layered)."""
    if not rpm_available():
        return False
    try:
        result = subprocess.run(
            ["rpm", "-q", pkg],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def rpm_ostree_status_raw() -> dict:
    """Roda `rpm-ostree status --json` e retorna o JSON parseado.
    Retorna {} se falhar."""
    if not rpm_ostree_available():
        return {}
    try:
        result = subprocess.run(
            ["rpm-ostree", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return {}
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        return {}


def pending_changes() -> PendingChanges:
    """Analisa `rpm-ostree status` para detectar mudancas pendentes.

    Heuristica:
    - Existem deployments. O booted=True e' o atual; o staged=True e'
      o pending (sera ativado no proximo boot).
    - Diff entre `requested-packages` do staged vs do booted = added.
    - Removidos = no booted mas nao no staged.
    """
    data = rpm_ostree_status_raw()
    result = PendingChanges()

    deployments = data.get("deployments", []) or []
    booted = next((d for d in deployments if d.get("booted")), None)
    staged = next((d for d in deployments if d.get("staged")), None)

    if booted:
        result.current_layered = list(booted.get("requested-packages", []) or [])

    if staged:
        result.has_pending = True
        staged_pkgs = set(staged.get("requested-packages", []) or [])
        booted_pkgs = set(result.current_layered)
        result.pending_added = sorted(staged_pkgs - booted_pkgs)
        result.pending_removed = sorted(booted_pkgs - staged_pkgs)

    return result


# ============================================================
# Install / Uninstall (UM pkexec por operacao em lote)
# ============================================================


def install_packages_blocking(packages: list[str]) -> tuple[bool, str]:
    """`pkexec rpm-ostree install <pkgs...>`. Bloqueante."""
    if not packages:
        return False, "Nenhum pacote selecionado."
    if not rpm_ostree_available():
        return False, "rpm-ostree nao encontrado (este sistema nao e' atomico?)."

    cmd = ["pkexec", "rpm-ostree", "install", "--idempotent"] + list(packages)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=900,
        )
    except subprocess.TimeoutExpired:
        return False, "rpm-ostree install demorou mais de 15 minutos."
    except FileNotFoundError:
        return False, "pkexec ou rpm-ostree nao encontrado."

    if result.returncode in (126, 127):
        return False, "Autenticacao cancelada."
    if result.returncode != 0:
        out = (result.stderr or result.stdout or "").strip()
        return False, f"Falha (codigo {result.returncode}):\n\n{out[:800]}"

    return True, result.stdout.strip()


def uninstall_packages_blocking(packages: list[str]) -> tuple[bool, str]:
    """`pkexec rpm-ostree uninstall <pkgs...>`. Bloqueante."""
    if not packages:
        return False, "Nenhum pacote selecionado."
    if not rpm_ostree_available():
        return False, "rpm-ostree nao encontrado."

    cmd = ["pkexec", "rpm-ostree", "uninstall"] + list(packages)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600,
        )
    except subprocess.TimeoutExpired:
        return False, "rpm-ostree uninstall demorou mais de 10 minutos."
    except FileNotFoundError:
        return False, "pkexec ou rpm-ostree nao encontrado."

    if result.returncode in (126, 127):
        return False, "Autenticacao cancelada."
    if result.returncode != 0:
        out = (result.stderr or result.stdout or "").strip()
        return False, f"Falha (codigo {result.returncode}):\n\n{out[:800]}"

    return True, result.stdout.strip()


def reboot_system() -> tuple[bool, str]:
    """`pkexec systemctl reboot`. Bloqueante (mas obviamente a UI nao
    volta — sistema vai reiniciar)."""
    cmd = ["pkexec", "systemctl", "reboot"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except subprocess.TimeoutExpired:
        return False, "systemctl reboot demorou demais."
    except FileNotFoundError:
        return False, "pkexec ou systemctl nao encontrado."

    if result.returncode in (126, 127):
        return False, "Autenticacao cancelada."
    if result.returncode != 0:
        return False, (result.stderr or "Falha desconhecida").strip()
    return True, ""
