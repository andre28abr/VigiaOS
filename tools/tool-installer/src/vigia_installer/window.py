"""Janela principal — 2 tabs (Catalogo + Pendentes).

Suporta modo standalone (VigiaInstallerWindow) e embedded (build_content()).
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .tabs import BrowseTab, PendingTab


class _InstallerContent:
    def __init__(self) -> None:
        self.pending = PendingTab(on_changed=lambda: None)
        self.browse = BrowseTab(on_changed=self._on_browse_changed)

        stack = Adw.ViewStack()
        stack.add_titled_with_icon(self.browse, "browse", "Catalogo", "package-x-generic-symbolic")
        stack.add_titled_with_icon(self.pending, "pending", "Pendentes", "view-refresh-symbolic")

        switcher = Adw.ViewSwitcher()
        switcher.set_stack(stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)

        header = Adw.HeaderBar()
        header.set_title_widget(switcher)

        self.toolbar = Adw.ToolbarView()
        self.toolbar.add_top_bar(header)
        self.toolbar.set_content(stack)

    def _on_browse_changed(self) -> None:
        """Apos install/uninstall, atualiza tab Pendentes."""
        self.pending.refresh()


def build_content() -> Gtk.Widget:
    ctrl = _InstallerContent()
    ctrl.toolbar._controller = ctrl  # type: ignore[attr-defined]
    return ctrl.toolbar


class VigiaInstallerWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("Tool Installer")
        self.set_default_size(900, 720)
        self.set_content(build_content())
