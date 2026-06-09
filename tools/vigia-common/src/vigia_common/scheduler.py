"""Agendamento via **systemd user timer** (sem root, escopo do usuário).

Gera os arquivos .service/.timer em ~/.config/systemd/user/ e os habilita pelo
`systemctl --user`. A geração de conteúdo é pura/testável; as chamadas ao
systemctl são finas e à prova de erro.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

_UNIT_DIR = Path.home() / ".config" / "systemd" / "user"


def service_unit(description: str, exec_cmd: str) -> str:
    return (
        "[Unit]\n"
        f"Description={description}\n\n"
        "[Service]\n"
        "Type=oneshot\n"
        f"ExecStart={exec_cmd}\n"
    )


def timer_unit(description: str, on_calendar: str) -> str:
    return (
        "[Unit]\n"
        f"Description={description}\n\n"
        "[Timer]\n"
        f"OnCalendar={on_calendar}\n"
        "Persistent=true\n\n"
        "[Install]\n"
        "WantedBy=timers.target\n"
    )


def _systemctl(*args: str) -> bool:
    if not shutil.which("systemctl"):
        return False
    try:
        r = subprocess.run(["systemctl", "--user", *args],
                           capture_output=True, text=True, timeout=15)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def install_timer(name: str, description: str, exec_cmd: str,
                  on_calendar: str = "weekly") -> bool:
    """Cria/atualiza <name>.service + <name>.timer e habilita o timer."""
    try:
        _UNIT_DIR.mkdir(parents=True, exist_ok=True)
        (_UNIT_DIR / f"{name}.service").write_text(
            service_unit(description, exec_cmd), encoding="utf-8")
        (_UNIT_DIR / f"{name}.timer").write_text(
            timer_unit(description, on_calendar), encoding="utf-8")
    except OSError:
        return False
    _systemctl("daemon-reload")
    return _systemctl("enable", "--now", f"{name}.timer")


def remove_timer(name: str) -> bool:
    """Desabilita o timer e apaga os units."""
    _systemctl("disable", "--now", f"{name}.timer")
    ok = True
    for suffix in (".timer", ".service"):
        p = _UNIT_DIR / f"{name}{suffix}"
        try:
            if p.exists():
                p.unlink()
        except OSError:
            ok = False
    _systemctl("daemon-reload")
    return ok


def timer_enabled(name: str) -> bool:
    if not shutil.which("systemctl"):
        return False
    try:
        r = subprocess.run(["systemctl", "--user", "is-enabled",
                            f"{name}.timer"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() == "enabled"
    except (OSError, subprocess.SubprocessError):
        return False
