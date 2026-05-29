"""Janela principal — orquestra 4 tabs e mantem o LynisReport corrente.

Suporta modo standalone (VigiaHardeningWindow) e embedded (build_content()).
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from vigia_common.notifications import PRIORITY_HIGH, notify_if_unfocused

from . import WRAPPED_PACKAGES
from .backend import LynisReport, parse_report
from .tabs import AboutTab, CategoriesTab, OverviewTab, SuggestionsTab, WarningsTab


def _make_pkg_badges_bar() -> Gtk.Widget:
    """Sub-bar abaixo do header com badges dos pacotes 'wrapped'."""
    bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    bar.set_margin_start(12)
    bar.set_margin_end(12)
    bar.set_margin_top(4)
    bar.set_margin_bottom(4)
    intro = Gtk.Label(label="Wrapper de:")
    intro.add_css_class("caption")
    intro.add_css_class("dim-label")
    bar.append(intro)
    for pkg in WRAPPED_PACKAGES:
        pill = Gtk.Label(label=pkg)
        pill.add_css_class("monospace")
        pill.add_css_class("caption")
        pill.add_css_class("dim-label")
        bar.append(pill)
    return bar


class _HardeningContent:
    """Controller interno: encapsula state (report) + callback de refresh."""

    def __init__(self) -> None:
        self._report: LynisReport = parse_report()

        self.overview = OverviewTab(on_audit_done=self._reload_and_refresh)
        self.warnings = WarningsTab()
        self.suggestions = SuggestionsTab()
        self.categories = CategoriesTab()
        self.about = AboutTab()
        self._tabs = (self.overview, self.warnings, self.suggestions, self.categories)

        self.toolbar = self._build_toolbar()
        self._refresh_all()

    def _build_toolbar(self) -> Adw.ToolbarView:
        stack = Adw.ViewStack()
        stack.add_titled_with_icon(self.overview, "overview", "Resumo", "dialog-information-symbolic")
        stack.add_titled_with_icon(self.warnings, "warnings", "Warnings", "dialog-warning-symbolic")
        stack.add_titled_with_icon(self.suggestions, "suggestions", "Suggestions", "starred-symbolic")
        stack.add_titled_with_icon(self.categories, "categories", "Categorias", "view-list-symbolic")
        stack.add_titled_with_icon(self.about, "about", "Sobre", "help-about-symbolic")

        switcher = Adw.ViewSwitcher()
        switcher.set_stack(stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)

        header = Adw.HeaderBar()
        header.set_title_widget(switcher)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        if WRAPPED_PACKAGES:
            toolbar.add_top_bar(_make_pkg_badges_bar())
        toolbar.set_content(stack)
        return toolbar

    def _reload_and_refresh(self) -> None:
        self._report = parse_report()
        self._refresh_all()
        self._notify_audit()

    def _notify_audit(self) -> None:
        """Banner desktop quando a auditoria Lynis termina e o user nao
        esta olhando a janela (minimizado/tray ou em outro app)."""
        report = self._report
        if not report.has_data():
            return
        n_warn = len(report.warnings)
        n_sug = len(report.suggestions)
        idx = report.hardening_index
        idx_txt = f"Hardening index {idx}/100. " if idx is not None else ""
        if n_warn > 0:
            notify_if_unfocused(
                f"Hardening: {n_warn} warning(s)",
                f"{idx_txt}{n_sug} sugestão(ões). Abra o Vigia pra revisar.",
                notif_id="vigia-hardening-audit",
                priority=PRIORITY_HIGH,
            )
        else:
            notify_if_unfocused(
                "Hardening: nenhum warning",
                f"{idx_txt}{n_sug} sugestão(ões) de melhoria.",
                notif_id="vigia-hardening-audit",
            )

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
