"""Backend de pacotes do Tool Installer (Fedora Workstation, dnf).

Operacoes:
- is_package_installed(pkg) -> bool                       (via `rpm -q`)
- install_packages_blocking(pkgs) -> (success, output)    (pkexec dnf install -y)
- uninstall_packages_blocking(pkgs) -> (success, output)  (pkexec dnf remove -y)
- check_updates() -> UpdateInfo                           (dnf check-update)
- run_system_update_blocking() -> (success, output)       (pkexec dnf upgrade -y)

Tudo via **pkexec** com argv-list (nunca shell string com input do usuario).
O dnf aplica na hora — sem o conceito de "mudancas pendentes / reboot".
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

from vigia_common.notices import Notification

from .catalog import is_suite_package


# ============================================================
# Sanity
# ============================================================


def rpm_available() -> bool:
    return shutil.which("rpm") is not None


# ============================================================
# Status (pacote instalado?)
# ============================================================


def is_package_installed(pkg: str) -> bool:
    """Verifica via `rpm -q <pkg>` (a base RPM existe no Workstation)."""
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


# ============================================================
# Install / Uninstall (UM pkexec por operacao em lote)
# ============================================================


def _run_pkg_cmd(cmd: list[str], timeout: int, label: str) -> tuple[bool, str]:
    """Roda um comando de pacote (dnf via pkexec) e normaliza o resultado.
    returncode 126/127 = autenticacao pkexec cancelada."""
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
    """Instala pacotes (bloqueante) via `pkexec dnf install -y` — aplica na
    hora, sem reboot."""
    if not packages:
        return False, "Nenhum pacote selecionado."
    cmd = ["pkexec", "dnf", "install", "-y"] + list(packages)
    return _run_pkg_cmd(cmd, 900, "dnf install")


def uninstall_packages_blocking(packages: list[str]) -> tuple[bool, str]:
    """Remove pacotes (bloqueante) via `pkexec dnf remove -y`."""
    if not packages:
        return False, "Nenhum pacote selecionado."
    cmd = ["pkexec", "dnf", "remove", "-y"] + list(packages)
    return _run_pkg_cmd(cmd, 600, "dnf remove")


# ============================================================
# Atualizacoes do sistema (dnf upgrade)
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
    return ["dnf", "check-update"]


def update_command(elevated: bool = False) -> list[str]:
    """Comando que *aplica* a atualizacao do sistema (`dnf upgrade -y`). Com
    `elevated`, prefixa pkexec (uso no painel do Hub)."""
    base = ["dnf", "upgrade", "-y"]
    return (["pkexec"] + base) if elevated else base


def update_command_display() -> str:
    """Comando amigavel pro usuario copiar e rodar no proprio terminal."""
    return "sudo dnf upgrade"


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


def split_updates(packages: list[str]) -> tuple[list[str], list[str]]:
    """Separa a lista de pacotes com update em (suíte, sistema). 'suíte' = o
    que `is_suite_package` reconhece (catálogo Vigia ou pacotes `vigia-*`); o
    resto é considerado pacote do sistema. Mantém a ordem de entrada."""
    suite: list[str] = []
    system: list[str] = []
    for pkg in packages:
        (suite if is_suite_package(pkg) else system).append(pkg)
    return suite, system


def check_updates() -> UpdateInfo:
    """Checa se ha atualizacoes do sistema (`dnf check-update`). Read-only:
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
    """Aplica a atualizacao do sistema via `pkexec dnf upgrade -y`
    (bloqueante e LONGO). No Workstation, aplica na hora."""
    return _run_pkg_cmd(
        update_command(elevated=True), 1800, "atualização do sistema")


def updates_to_notifications(info: "UpdateInfo") -> "list[Notification]":
    """Converte um UpdateInfo numa lista de Notification (pro sininho do Hub).
    Vazia quando nao ha update. Separa sistema vs programas da suite."""
    if not (info.checked and info.available):
        return []
    suite, system = split_updates(info.packages)
    out: list[Notification] = []
    if system or not info.packages:
        n = len(system)
        out.append(Notification(
            "Atualização do sistema disponível",
            (f"{n} pacote(s) do sistema operacional."
             if n else "Há novidades do sistema para baixar."),
            "software-update-available-symbolic",
        ))
    if suite:
        nomes = ", ".join(suite[:3]) + ("…" if len(suite) > 3 else "")
        out.append(Notification(
            "Atualização de programas da suíte",
            f"{len(suite)} programa(s): {nomes}",
            "application-x-executable-symbolic",
        ))
    return out
