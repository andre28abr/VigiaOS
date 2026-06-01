"""Agendamento automático via **systemd user timer** (sem root).

Escreve uma `.service` (oneshot que roda `vigia-reports --generate …`) + uma
`.timer` (dia 1 de cada mês, `Persistent`) em `~/.config/systemd/user/` e
habilita com `systemctl --user`. Tudo no escopo do usuário.

Os construtores de unit (`build_service_unit`/`build_timer_unit`) são puros e
testáveis; só `enable_schedule`/`disable_schedule` tocam o systemctl.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

UNIT_DIR = Path.home() / ".config" / "systemd" / "user"
SERVICE = UNIT_DIR / "vigia-reports.service"
TIMER = UNIT_DIR / "vigia-reports.timer"


def _exec_path() -> str:
    return shutil.which("vigia-reports") or str(
        Path.home() / ".local" / "bin" / "vigia-reports"
    )


def build_service_unit(template_id: str, period: int, exec_path: str) -> str:
    return (
        "[Unit]\n"
        "Description=Vigia Reports - geracao automatica de relatorio\n\n"
        "[Service]\n"
        "Type=oneshot\n"
        f"ExecStart={exec_path} --generate {template_id} --period {period}\n"
    )


def build_timer_unit() -> str:
    return (
        "[Unit]\n"
        "Description=Vigia Reports - timer mensal\n\n"
        "[Timer]\n"
        "OnCalendar=*-*-01 09:00:00\n"   # dia 1 de cada mes, 09h
        "Persistent=true\n\n"            # roda no proximo boot se a maquina estava off
        "[Install]\n"
        "WantedBy=timers.target\n"
    )


def _systemctl(*args: str) -> tuple[bool, str]:
    if shutil.which("systemctl") is None:
        return False, "systemctl não encontrado."
    try:
        r = subprocess.run(
            ["systemctl", "--user", *args],
            capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    return r.returncode == 0, (r.stderr or r.stdout).strip()


def is_enabled() -> bool:
    ok, out = _systemctl("is-enabled", "vigia-reports.timer")
    return ok and out.strip() == "enabled"


def scheduled_model() -> str | None:
    """Lê o modelo agendado a partir do ExecStart da .service (ou None)."""
    if not SERVICE.is_file():
        return None
    try:
        for line in SERVICE.read_text(encoding="utf-8").splitlines():
            if line.startswith("ExecStart=") and "--generate" in line:
                parts = line.split()
                i = parts.index("--generate")
                return parts[i + 1] if i + 1 < len(parts) else None
    except OSError:
        pass
    return None


def enable_schedule(template_id: str, period: int = 30) -> tuple[bool, str]:
    UNIT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        SERVICE.write_text(
            build_service_unit(template_id, period, _exec_path()), encoding="utf-8"
        )
        TIMER.write_text(build_timer_unit(), encoding="utf-8")
    except OSError as e:
        return False, f"Falha ao escrever os arquivos do timer: {e}"
    _systemctl("daemon-reload")
    ok, msg = _systemctl("enable", "--now", "vigia-reports.timer")
    return ok, ("" if ok else (msg or "Falha ao habilitar o timer."))


def disable_schedule() -> tuple[bool, str]:
    ok, msg = _systemctl("disable", "--now", "vigia-reports.timer")
    return ok, ("" if ok else msg)
