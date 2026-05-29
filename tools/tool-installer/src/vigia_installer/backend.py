"""Backend de pacotes: rpm-ostree (sistema atomico) ou dnf (Workstation).

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

from vigia_common.platform import is_atomic


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
        data = json.loads(result.stdout)
        # HARDENING: garante dict no topo (rpm-ostree corrompido/inesperado).
        return data if isinstance(data, dict) else {}
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
    # HARDENING: robusto mesmo se a fonte mudar de contrato.
    if not isinstance(data, dict):
        return result

    deployments = data.get("deployments", [])
    if not isinstance(deployments, list):
        deployments = []
    booted = next((d for d in deployments
                   if isinstance(d, dict) and d.get("booted")), None)
    staged = next((d for d in deployments
                   if isinstance(d, dict) and d.get("staged")), None)

    if booted:
        layered = booted.get("requested-packages", [])
        result.current_layered = list(layered) if isinstance(layered, list) else []

    if staged:
        result.has_pending = True
        staged_layered = staged.get("requested-packages", [])
        staged_pkgs = set(staged_layered) if isinstance(staged_layered, list) else set()
        booted_pkgs = set(result.current_layered)
        result.pending_added = sorted(staged_pkgs - booted_pkgs)
        result.pending_removed = sorted(booted_pkgs - staged_pkgs)

    return result


# ============================================================
# Install / Uninstall (UM pkexec por operacao em lote)
# ============================================================


def _run_pkg_cmd(cmd: list[str], timeout: int, label: str) -> tuple[bool, str]:
    """Roda um comando de pacote (rpm-ostree/dnf via pkexec) e normaliza
    o resultado. returncode 126/127 = autenticacao pkexec cancelada."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"{label} excedeu o tempo limite."
    except FileNotFoundError:
        return False, "pkexec ou gerenciador de pacotes nao encontrado."

    if result.returncode in (126, 127):
        return False, "Autenticacao cancelada."
    if result.returncode != 0:
        out = (result.stderr or result.stdout or "").strip()
        return False, f"Falha (codigo {result.returncode}):\n\n{out[:800]}"

    return True, result.stdout.strip()


def install_packages_blocking(packages: list[str]) -> tuple[bool, str]:
    """Instala pacotes (bloqueante). Em sistema **atomico** usa
    `rpm-ostree install --idempotent` (precisa reboot pra aplicar); no
    **Workstation** tradicional usa `dnf install -y` (aplica na hora)."""
    if not packages:
        return False, "Nenhum pacote selecionado."
    pkgs = list(packages)
    if is_atomic():
        cmd = ["pkexec", "rpm-ostree", "install", "--idempotent"] + pkgs
        return _run_pkg_cmd(cmd, 900, "rpm-ostree install")
    cmd = ["pkexec", "dnf", "install", "-y"] + pkgs
    return _run_pkg_cmd(cmd, 900, "dnf install")


def uninstall_packages_blocking(packages: list[str]) -> tuple[bool, str]:
    """Remove pacotes (bloqueante). Atomico: `rpm-ostree uninstall`;
    Workstation: `dnf remove -y`."""
    if not packages:
        return False, "Nenhum pacote selecionado."
    pkgs = list(packages)
    if is_atomic():
        cmd = ["pkexec", "rpm-ostree", "uninstall"] + pkgs
        return _run_pkg_cmd(cmd, 600, "rpm-ostree uninstall")
    cmd = ["pkexec", "dnf", "remove", "-y"] + pkgs
    return _run_pkg_cmd(cmd, 600, "dnf remove")


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
