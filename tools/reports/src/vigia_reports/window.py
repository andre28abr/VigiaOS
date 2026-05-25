"""Janela principal — orquestra 2 tabs (Gerar + Biblioteca).

Suporta modo standalone (VigiaReportsWindow) e embedded (build_content()).
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .tabs import GenerateTab, LibraryTab


class _ReportsContent:
    def __init__(self) -> None:
        self.library = LibraryTab()
        self.generate = GenerateTab(on_report_generated=self.library.refresh)

        stack = Adw.ViewStack()
        stack.add_titled_with_icon(self.generate, "generate", "Gerar", "document-new-symbolic")
        stack.add_titled_with_icon(self.library, "library", "Biblioteca", "view-list-symbolic")

        switcher = Adw.ViewSwitcher()
        switcher.set_stack(stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)

        header = Adw.HeaderBar()
        header.set_title_widget(switcher)

        self.toolbar = Adw.ToolbarView()
        self.toolbar.add_top_bar(header)
        self.toolbar.set_content(stack)


def build_content() -> Gtk.Widget:
    ctrl = _ReportsContent()
    ctrl.toolbar._controller = ctrl  # type: ignore[attr-defined]
    return ctrl.toolbar


class VigiaReportsWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("Reports")
        self.set_default_size(820, 720)
        self.set_content(build_content())
