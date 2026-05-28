"""Gerenciamento de tema (dark/light/system) via Adw.StyleManager.

Adwaita 1+ tem 3 modos:
- DEFAULT: segue preferencia do sistema (light/dark conforme GNOME)
- FORCE_LIGHT: forca light theme
- FORCE_DARK: forca dark theme

Aplica no app inteiro (Hub + tools embedded).
"""

from __future__ import annotations

from typing import Literal

ThemeMode = Literal["system", "light", "dark"]

VALID_MODES: tuple[ThemeMode, ...] = ("system", "light", "dark")


def apply_theme(mode: ThemeMode) -> None:
    """Aplica modo de tema. Falha silenciosamente se Adw nao disponivel."""
    try:
        import gi
        gi.require_version("Adw", "1")
        from gi.repository import Adw
    except (ValueError, ImportError):
        return

    sm = Adw.StyleManager.get_default()
    if mode == "dark":
        sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
    elif mode == "light":
        sm.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
    else:  # system
        sm.set_color_scheme(Adw.ColorScheme.DEFAULT)


def normalize_mode(raw: str) -> ThemeMode:
    """Normaliza string pra ThemeMode valido. Default = system."""
    if raw in VALID_MODES:
        return raw  # type: ignore[return-value]
    return "system"
