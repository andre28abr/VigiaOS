"""Janela principal — thin orchestrator das 2 tabs (Status + Zones).

Suporta modo standalone (VigiaFirewallWindow) e embedded (build_content()).
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .tabs import StatusTab, ZonesTab


TABS = [
    ("status", "Status", "dialog-information-symbolic", StatusTab),
    ("zones", "Zonas", "preferences-system-symbolic", ZonesTab),
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


class VigiaFirewallWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("Firewall Manager")
        self.set_default_size(820, 680)
        self.set_content(build_content())
