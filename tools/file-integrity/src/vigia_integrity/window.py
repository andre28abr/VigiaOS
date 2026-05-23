"""Janela principal — orquestra 3 tabs (Status + Mudancas + Sobre)."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw  # noqa: E402

from .backend import CheckResult
from .tabs import AboutTab, ChangesTab, StatusTab


class VigiaIntegrityWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("File Integrity")
        self.set_default_size(900, 720)

        self._status = StatusTab(on_check_done=self._on_check_done)
        self._changes = ChangesTab()
        self._about = AboutTab()

        self._stack = Adw.ViewStack()
        self._stack.add_titled_with_icon(self._status, "status", "Status", "dialog-information-symbolic")
        self._stack.add_titled_with_icon(self._changes, "changes", "Mudancas", "view-list-symbolic")
        self._stack.add_titled_with_icon(self._about, "about", "Sobre", "help-about-symbolic")

        switcher = Adw.ViewSwitcher()
        switcher.set_stack(self._stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)

        header = Adw.HeaderBar()
        header.set_title_widget(switcher)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(self._stack)
        self.set_content(toolbar)

    def _on_check_done(self, result: CheckResult) -> None:
        self._changes.refresh(result.changes)
