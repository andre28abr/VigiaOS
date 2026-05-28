"""Settings do Hub — persistencia local + autostart XDG.

Arquivo: ~/.config/vigia-hub/settings.json (mode 0600 — LGPD)

Formato:
{
  "autostart": true,
  "show_tray": false,
  "start_minimized": false,
  "password_lock": false
}

Autostart segue padrao XDG: ~/.config/autostart/vigia-hub.desktop
(funciona em GNOME, KDE, XFCE e qualquer DE conformante).
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


STATE_DIR = Path.home() / ".config" / "vigia-hub"
STATE_PATH = STATE_DIR / "settings.json"

AUTOSTART_DIR = Path.home() / ".config" / "autostart"
AUTOSTART_PATH = AUTOSTART_DIR / "vigia-hub.desktop"


@dataclass
class Settings:
    autostart: bool = False
    show_tray: bool = False
    start_minimized: bool = False
    password_lock: bool = False


# ============================================================
# Persistencia (JSON)
# ============================================================


def load_settings() -> Settings:
    """Le settings file. Retorna defaults se nao existe ou erro."""
    if not STATE_PATH.exists():
        return Settings()
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Settings(
            autostart=bool(data.get("autostart", False)),
            show_tray=bool(data.get("show_tray", False)),
            start_minimized=bool(data.get("start_minimized", False)),
            password_lock=bool(data.get("password_lock", False)),
        )
    except (OSError, json.JSONDecodeError) as e:
        print(f"[settings] load falhou: {e}", flush=True)
        return Settings()


def save_settings(s: Settings) -> bool:
    """Salva atomico em ~/.config/vigia-hub/settings.json (0600)."""
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        os.chmod(STATE_DIR, 0o700)
        tmp = STATE_PATH.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(asdict(s), f, ensure_ascii=False, indent=2)
        os.chmod(tmp, 0o600)
        tmp.replace(STATE_PATH)
        return True
    except OSError as e:
        print(f"[settings] save falhou: {e}", flush=True)
        return False


# ============================================================
# Autostart XDG
# ============================================================


def _build_desktop_content(minimized: bool = False) -> str:
    """Conteudo do .desktop pra autostart.

    minimized=True adiciona --minimized ao Exec (usado quando o user
    habilita "iniciar minimizado" + tray — implementado em Fase 1b).
    """
    exec_line = "vigia-hub --minimized" if minimized else "vigia-hub"
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Vigia Hub\n"
        "Comment=Launcher da Vigia Suite\n"
        f"Exec={exec_line}\n"
        "Icon=br.com.vigia.Hub\n"
        "Terminal=false\n"
        "Categories=System;Security;\n"
        "X-GNOME-Autostart-enabled=true\n"
        "X-GNOME-Autostart-Delay=10\n"
    )


def autostart_is_enabled() -> bool:
    """True se ~/.config/autostart/vigia-hub.desktop existe."""
    return AUTOSTART_PATH.is_file()


def autostart_install(minimized: bool = False) -> bool:
    """Cria ~/.config/autostart/vigia-hub.desktop."""
    try:
        AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
        AUTOSTART_PATH.write_text(
            _build_desktop_content(minimized=minimized),
            encoding="utf-8",
        )
        os.chmod(AUTOSTART_PATH, 0o644)
        return True
    except OSError as e:
        print(f"[settings] autostart_install falhou: {e}", flush=True)
        return False


def autostart_remove() -> bool:
    """Remove ~/.config/autostart/vigia-hub.desktop."""
    try:
        if AUTOSTART_PATH.exists():
            AUTOSTART_PATH.unlink()
        return True
    except OSError as e:
        print(f"[settings] autostart_remove falhou: {e}", flush=True)
        return False


def autostart_sync(enabled: bool, minimized: bool = False) -> bool:
    """Helper: instala ou remove conforme flag."""
    if enabled:
        return autostart_install(minimized=minimized)
    return autostart_remove()
