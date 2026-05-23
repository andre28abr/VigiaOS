"""Janela principal — 2 tabs (Catalogo + Pendentes)."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw  # noqa: E402

from .tabs import BrowseTab, PendingTab


class VigiaInstallerWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("Tool Installer")
        self.set_default_size(900, 720)

        self._pending = PendingTab(on_changed=lambda: None)
        self._browse = BrowseTab(on_changed=self._on_browse_changed)

        self._stack = Adw.ViewStack()
        self._stack.add_titled_with_icon(self._browse, "browse", "Catalogo", "package-x-generic-symbolic")
        self._stack.add_titled_with_icon(self._pending, "pending", "Pendentes", "view-refresh-symbolic")

        switcher = Adw.ViewSwitcher()
        switcher.set_stack(self._stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)

        header = Adw.HeaderBar()
        header.set_title_widget(switcher)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(self._stack)
        self.set_content(toolbar)

    def _on_browse_changed(self) -> None:
        """Apos install/uninstall, atualiza tab Pendentes."""
        self._pending.refresh()
