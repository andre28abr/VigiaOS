"""Janela principal — orquestra 2 tabs (Gerar + Biblioteca)."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw  # noqa: E402

from .tabs import GenerateTab, LibraryTab


class VigiaReportsWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("Reports")
        self.set_default_size(820, 720)

        self._library = LibraryTab()
        self._generate = GenerateTab(on_report_generated=self._library.refresh)

        self._stack = Adw.ViewStack()
        self._stack.add_titled_with_icon(self._generate, "generate", "Gerar", "document-new-symbolic")
        self._stack.add_titled_with_icon(self._library, "library", "Biblioteca", "view-list-symbolic")

        switcher = Adw.ViewSwitcher()
        switcher.set_stack(self._stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)

        header = Adw.HeaderBar()
        header.set_title_widget(switcher)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(self._stack)
        self.set_content(toolbar)
