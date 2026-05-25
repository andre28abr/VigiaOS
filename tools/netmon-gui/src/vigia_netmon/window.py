"""Janela principal — thin orchestrator das 2 tabs (Connections + Listening).

Suporta modo standalone (VigiaNetmonWindow) e embedded (build_content()).
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .tabs import ConnectionsTab, ListeningTab


TABS = [
    ("connections", "Conexoes", "network-transmit-receive-symbolic", ConnectionsTab),
    ("listening",   "Listening", "network-server-symbolic",          ListeningTab),
]


def build_content() -> Gtk.Widget:
    """Constroi header + viewstack das 2 tabs como Adw.ToolbarView."""
    view_stack = Adw.ViewStack()
    for tab_id, title, icon, cls in TABS:
        view_stack.add_titled_with_icon(cls(), tab_id, title, icon)

    switcher = Adw.ViewSwitcher()
    switcher.set_stack(view_stack)
    switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)

    header = Adw.HeaderBar()
    header.set_title_widget(switcher)

    toolbar = Adw.ToolbarView()
    toolbar.add_top_bar(header)
    toolbar.set_content(view_stack)
    return toolbar


class VigiaNetmonWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("Network Monitor")
        self.set_default_size(1000, 700)
        self.set_content(build_content())
