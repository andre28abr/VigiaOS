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
        return False, "pkexec ou gerenciador de pacotes não encontrado."

    if result.returncode in (126, 127):
        return False, "Autenticação cancelada."
    if result.returncode != 0:
        out = (result.stderr or result.stdout or "").strip()
        return False, f"Falha (código {result.returncode}):\n\n{out[:800]}"

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
        return False, "pkexec ou systemctl não encontrado."

    if result.returncode in (126, 127):
        return False, "Autenticação cancelada."
    if result.returncode != 0:
        return False, (result.stderr or "Falha desconhecida").strip()
    return True, ""


# ============================================================
# Atualizacoes do sistema (rpm-ostree upgrade / dnf upgrade)
# ============================================================


@dataclass
class UpdateInfo:
    """Resultado de uma checagem de atualizacoes (NAO aplica nada)."""

    checked: bool = False        # a checagem rodou ate o fim?
    available: bool = False      # ha atualizacoes?
    packages: list[str] = None   # type: ignore[assignment]
    raw: str = ""                # saida bruta (pra expandir/depurar)
    error: str = ""              # mensagem (quando checked=False)

    def __post_init__(self) -> None:
        if self.packages is None:
            self.packages = []


def check_update_command() -> list[str]:
    """Comando de *checagem* (read-only, sem root, nao aplica nada)."""
    if is_atomic():
        return ["rpm-ostree", "upgrade", "--check"]
    return ["dnf", "check-update"]


def update_command(elevated: bool = False) -> list[str]:
    """Comando que *aplica* a atualizacao do sistema. Com `elevated`,
    prefixa pkexec (uso no painel do Hub). Sem ele, e' o comando base."""
    base = (["rpm-ostree", "upgrade"] if is_atomic()
            else ["dnf", "upgrade", "-y"])
    return (["pkexec"] + base) if elevated else base


def update_command_display() -> str:
    """Comando amigavel pro usuario copiar e rodar no proprio terminal."""
    return "rpm-ostree upgrade" if is_atomic() else "sudo dnf upgrade"


def parse_dnf_check_update(output: str) -> list[str]:
    """Nomes dos pacotes de `dnf check-update`. Cada update e' uma linha
    'nome.arch  versao  repo'. Ignora cabecalho, vazias e o bloco
    'Obsoleting Packages'."""
    pkgs: list[str] = []
    in_obsoleting = False
    for line in output.splitlines():
        s = line.strip()
        if not s:
            continue
        low = s.lower()
        if low.startswith("last metadata") or low.startswith("security:"):
            continue
        if low.startswith("obsoleting packages"):
            in_obsoleting = True
            continue
        if in_obsoleting:
            continue
        parts = s.split()
        # linha valida de update: >=3 colunas e a 1a traz '.arch'
        if len(parts) >= 3 and "." in parts[0] and not parts[0].endswith(":"):
            pkgs.append(parts[0].rsplit(".", 1)[0])
    return sorted(set(pkgs))


def parse_rpm_ostree_check(output: str) -> list[str]:
    """Best-effort: pacotes alterados no output de `rpm-ostree upgrade
    --check` (linhas com '->'). Pode vir vazio mesmo havendo update do
    base image — rpm-ostree nem sempre lista pacote-a-pacote."""
    pkgs: list[str] = []
    for line in output.splitlines():
        s = line.strip()
        if "->" in s and not s.lower().startswith("version"):
            tok = s.split()
            if tok:
                pkgs.append(tok[0].lstrip("+- "))
    return sorted(set(p for p in pkgs if p))


def check_updates() -> UpdateInfo:
    """Checa se ha atualizacoes do sistema (rpm-ostree / dnf). Read-only:
    nao precisa de root e nao altera nada. Robusta a erro/timeout."""
    info = UpdateInfo()
    cmd = check_update_command()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=180,
        )
    except subprocess.TimeoutExpired:
        info.error = "A checagem excedeu o tempo limite."
        return info
    except FileNotFoundError:
        info.error = f"{cmd[0]} não encontrado."
        return info

    info.raw = (result.stdout or "").strip()
    rc = result.returncode

    if is_atomic():
        # rpm-ostree upgrade --check: rc 0 = ha update; rc 77 = sem update.
        if rc == 77:
            info.checked, info.available = True, False
        elif rc == 0:
            low = info.raw.lower()
            if "no upgrade available" in low or "no updates" in low:
                info.checked, info.available = True, False
            else:
                info.checked, info.available = True, True
                info.packages = parse_rpm_ostree_check(info.raw)
        else:
            info.error = (result.stderr or info.raw
                          or "Falha na checagem.").strip()[:400]
    else:
        # dnf check-update: rc 100 = ha update; rc 0 = nenhum; outro = erro.
        if rc == 100:
            info.checked, info.available = True, True
            info.packages = parse_dnf_check_update(info.raw)
        elif rc == 0:
            info.checked, info.available = True, False
        else:
            info.error = (result.stderr or info.raw
                          or "Falha na checagem.").strip()[:400]

    return info


def run_system_update_blocking() -> tuple[bool, str]:
    """Aplica a atualizacao do sistema via pkexec (bloqueante e LONGO).
    Atomico: faz stage pra proximo boot; Workstation: aplica na hora."""
    return _run_pkg_cmd(
        update_command(elevated=True), 1800, "atualização do sistema")
