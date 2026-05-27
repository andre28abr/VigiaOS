"""Pytest config: adiciona src/ de cada tool ao sys.path.

Permite rodar tests sem instalar as tools via pip. Os imports ficam
como se as tools estivessem instaladas (`from vigia_common.helpers
import make_clamp`).

Tests que importam GTK/PyGObject sao skipados em ambientes sem ele
(ex: macOS dev sem `python3-gobject`).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"


def _add_tool_to_path(tool_dirname: str) -> None:
    """Adiciona tools/<dirname>/src ao sys.path."""
    src = TOOLS_DIR / tool_dirname / "src"
    if src.is_dir():
        path_str = str(src)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)


# Tools a serem testaveis (todas, menos activity-log que e' Rust)
TOOLS = [
    "vigia-common",
    "vigia-hub",
    "activity-log-gui",
    "privacy-controls",
    "selinux-gui",
    "firewall-gui",
    "netmon-gui",
    "hardening-checks",
    "reports",
    "file-integrity",
    "tool-installer",
    "vpn-manager",
    "dns-manager",
    "capabilities-inspector",
    "antivirus",
    "network-scanner",
    "firmware-analyzer",
    "hash-tools",
    "dashboard",
    "rootkit-scanner",
]

for tool in TOOLS:
    _add_tool_to_path(tool)


# Detecta se PyGObject esta disponivel (gtk4)
HAS_GI = False
try:
    import gi  # noqa: F401
    HAS_GI = True
except ImportError:
    pass


def pytest_collection_modifyitems(config, items):
    """Skipa tests marcados @pytest.mark.gtk se GTK nao disponivel."""
    import pytest
    skip_gtk = pytest.mark.skip(reason="PyGObject/GTK4 nao instalado (ambiente sem GI)")
    for item in items:
        if "gtk" in item.keywords and not HAS_GI:
            item.add_marker(skip_gtk)
