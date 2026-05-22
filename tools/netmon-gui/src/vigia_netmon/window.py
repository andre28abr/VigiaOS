"""Janela principal — thin orchestrator das 2 tabs (Connections + Listening)."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw  # noqa: E402

from .tabs import ConnectionsTab, ListeningTab


TABS = [
    ("connections", "Conexoes", "network-transmit-receive-symbolic", ConnectionsTab),
    ("listening",   "Listening", "network-server-symbolic",          ListeningTab),
]


class VigiaNetmonWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("Network Monitor")
        self.set_default_size(1000, 700)

        self.view_stack = Adw.ViewStack()
        for tab_id, title, icon, cls in TABS:
            self.view_stack.add_titled_with_icon(cls(), tab_id, title, icon)

        switcher = Adw.ViewSwitcher()
        switcher.set_stack(self.view_stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)

        header = Adw.HeaderBar()
        header.set_title_widget(switcher)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(self.view_stack)
        self.set_content(toolbar)
