"""Janela principal — thin orchestrator que monta as 6 tabs.

A logica especifica de cada tab vive em tabs/<nome>.py.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .tabs import (
    BooleansTab,
    DenialsTab,
    FilesTab,
    NetworkTab,
    ProcessesTab,
    StatusTab,
)


# Cada entry: (id, titulo, icon, classe da tab)
TABS = [
    ("status",    "Status",    "dialog-information-symbolic", StatusTab),
    ("booleans",  "Booleans",  "preferences-system-symbolic", BooleansTab),
    ("denials",   "Denials",   "dialog-warning-symbolic",     DenialsTab),
    ("files",     "Files",     "folder-symbolic",             FilesTab),
    ("network",   "Network",   "network-wired-symbolic",      NetworkTab),
    ("processes", "Processes", "system-run-symbolic",         ProcessesTab),
]


class VigiaSelinuxWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("SELinux Manager")
        self.set_default_size(900, 680)

        # ViewStack com as tabs
        self.view_stack = Adw.ViewStack()
        for tab_id, title, icon, cls in TABS:
            tab_widget = cls()
            self.view_stack.add_titled_with_icon(tab_widget, tab_id, title, icon)

        # ViewSwitcher no header
        switcher = Adw.ViewSwitcher()
        switcher.set_stack(self.view_stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)

        header = Adw.HeaderBar()
        header.set_title_widget(switcher)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(self.view_stack)
        self.set_content(toolbar)
