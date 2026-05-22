"""Toggle: power do adapter Bluetooth (via bluetoothctl)."""

from __future__ import annotations

import shutil
import subprocess

from .base import Toggle


def _has_bluetoothctl() -> bool:
    return shutil.which("bluetoothctl") is not None


def _available() -> bool:
    if not _has_bluetoothctl():
        return False
    # Checa se ha pelo menos um controller
    try:
        out = subprocess.run(
            ["bluetoothctl", "list"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return out.returncode == 0 and bool(out.stdout.strip())
    except subprocess.SubprocessError:
        return False


def _get() -> bool:
    """True se o controller principal esta com Powered=yes."""
    out = subprocess.run(
        ["bluetoothctl", "show"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    return "Powered: yes" in out.stdout


def _set(value: bool) -> None:
    subprocess.run(
        ["bluetoothctl", "power", "on" if value else "off"],
        capture_output=True,
        check=True,
        timeout=5,
    )


TOGGLE = Toggle(
    name="Bluetooth",
    description="Liga/desliga o adapter Bluetooth principal. Quando OFF, "
    "nenhum dispositivo Bluetooth pode parear ou conectar.",
    category="Dispositivos",
    get_fn=_get,
    set_fn=_set,
    available_fn=_available,
)
