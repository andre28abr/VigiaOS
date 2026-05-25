"""Janela principal — orquestra 4 tabs e mantem o LynisReport corrente.

Suporta modo standalone (VigiaHardeningWindow) e embedded (build_content()).
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .backend import LynisReport, parse_report
from .tabs import CategoriesTab, OverviewTab, SuggestionsTab, WarningsTab


class _HardeningContent:
    """Controller interno: encapsula state (report) + callback de refresh."""

    def __init__(self) -> None:
        self._report: LynisReport = parse_report()

        self.overview = OverviewTab(on_audit_done=self._reload_and_refresh)
        self.warnings = WarningsTab()
        self.suggestions = SuggestionsTab()
        self.categories = CategoriesTab()
        self._tabs = (self.overview, self.warnings, self.suggestions, self.categories)

        self.toolbar = self._build_toolbar()
        self._refresh_all()

    def _build_toolbar(self) -> Adw.ToolbarView:
        stack = Adw.ViewStack()
        stack.add_titled_with_icon(self.overview, "overview", "Resumo", "dialog-information-symbolic")
        stack.add_titled_with_icon(self.warnings, "warnings", "Warnings", "dialog-warning-symbolic")
        stack.add_titled_with_icon(self.suggestions, "suggestions", "Suggestions", "starred-symbolic")
        stack.add_titled_with_icon(self.categories, "categories", "Categorias", "view-list-symbolic")

        switcher = Adw.ViewSwitcher()
        switcher.set_stack(stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)

        header = Adw.HeaderBar()
        header.set_title_widget(switcher)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(stack)
        return toolbar

    def _reload_and_refresh(self) -> None:
        self._report = parse_report()
        self._refresh_all()

    def _refresh_all(self) -> None:
        for tab in self._tabs:
            tab.refresh(self._report)


def build_content() -> Gtk.Widget:
    """Retorna o conteudo principal como widget standalone ou para embed."""
    ctrl = _HardeningContent()
    ctrl.toolbar._controller = ctrl  # type: ignore[attr-defined]  # ancora pra evitar gc
    return ctrl.toolbar


class VigiaHardeningWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("Hardening Checks")
        self.set_default_size(900, 720)
        self.set_content(build_content())
