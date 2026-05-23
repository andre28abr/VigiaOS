"""Janela principal — orquestra 4 tabs e mantem o LynisReport corrente."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw  # noqa: E402

from .backend import LynisReport, parse_report
from .tabs import CategoriesTab, OverviewTab, SuggestionsTab, WarningsTab


class VigiaHardeningWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("Hardening Checks")
        self.set_default_size(900, 720)

        # State
        self._report: LynisReport = parse_report()

        # Tabs
        self._overview = OverviewTab(on_audit_done=self._reload_and_refresh)
        self._warnings = WarningsTab()
        self._suggestions = SuggestionsTab()
        self._categories = CategoriesTab()

        # ViewStack + Switcher
        self._stack = Adw.ViewStack()
        self._stack.add_titled_with_icon(self._overview, "overview", "Resumo", "dialog-information-symbolic")
        self._stack.add_titled_with_icon(self._warnings, "warnings", "Warnings", "dialog-warning-symbolic")
        self._stack.add_titled_with_icon(self._suggestions, "suggestions", "Suggestions", "starred-symbolic")
        self._stack.add_titled_with_icon(self._categories, "categories", "Categorias", "view-list-symbolic")

        switcher = Adw.ViewSwitcher()
        switcher.set_stack(self._stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)

        header = Adw.HeaderBar()
        header.set_title_widget(switcher)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(self._stack)
        self.set_content(toolbar)

        # Refresh inicial com o report ja em disco (se existir)
        self._refresh_all()

    def _reload_and_refresh(self) -> None:
        self._report = parse_report()
        self._refresh_all()

    def _refresh_all(self) -> None:
        self._overview.refresh(self._report)
        self._warnings.refresh(self._report)
        self._suggestions.refresh(self._report)
        self._categories.refresh(self._report)
