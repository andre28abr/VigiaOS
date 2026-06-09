"""vigia-scan — varredura de vírus (ClamAV) das pastas do usuário.

Pensado pra rodar **agendado** (systemd user timer, sem root): varre as pastas
mais comuns de download, notifica via `notify-send` se achar algo e grava o
resultado em ~/.local/share/vigia/last-scan.json (0600). Roda à mão também:
`vigia-scan`.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

_STATE = Path.home() / ".local" / "share" / "vigia" / "last-scan.json"
_DIRS = ["~/Downloads", "~/Documents", "~/Desktop", "~/Pictures"]


def _targets() -> list[str]:
    out = []
    for p in _DIRS:
        d = os.path.expanduser(p)
        if os.path.isdir(d):
            out.append(d)
    return out


def scan() -> dict:
    """Varre as pastas do usuário com clamscan. Devolve um dict de resultado."""
    targets = _targets()
    found: list[str] = []
    ran = False
    if shutil.which("clamscan") and targets:
        ran = True
        try:
            r = subprocess.run(
                ["clamscan", "-i", "-r", "--no-summary", *targets],
                capture_output=True, text=True, timeout=3600)
            if r.returncode == 1:  # 1 = encontrou vírus
                found = [ln for ln in r.stdout.splitlines() if ln.strip()]
        except (OSError, subprocess.SubprocessError):
            ran = False
    return {"ts": int(time.time()), "ran": ran,
            "found": len(found), "items": found[:30]}


def _write_state(state: dict) -> None:
    try:
        _STATE.parent.mkdir(parents=True, exist_ok=True)
        _STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                          encoding="utf-8")
        os.chmod(_STATE, 0o600)
    except OSError:
        pass


def _notify(title: str, body: str) -> None:
    if shutil.which("notify-send"):
        try:
            subprocess.run(["notify-send", "-a", "VigiaOS", title, body],
                           timeout=10)
        except (OSError, subprocess.SubprocessError):
            pass


def main() -> int:
    state = scan()
    _write_state(state)
    if state["found"]:
        _notify(f"{state['found']} ameaça(s) encontrada(s)",
                "A varredura de vírus achou algo. Abra o VigiaOS → Antivírus.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
