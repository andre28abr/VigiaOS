"""Janela principal — 4 tabs (Visao Geral + Binarios + Capabilities + Sobre)."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from . import WRAPPED_PACKAGES
from .backend import BinaryWithCaps
from .tabs import AboutTab, BinariesTab, CatalogTab, OverviewTab


def _make_pkg_badges_bar() -> Gtk.Widget:
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


class _CapsContent:
    """Controller: 4 tabs com state compartilhado (binaries do ultimo scan)."""

    def __init__(self) -> None:
        self.binaries: list[BinaryWithCaps] = []

        self.binaries_tab = BinariesTab()
        self.catalog_tab = CatalogTab()
        self.about_tab = AboutTab()
        self.overview_tab = OverviewTab(on_scan_done=self._on_scan_done)

        stack = Adw.ViewStack()
        stack.add_titled_with_icon(self.overview_tab, "overview", "Visão Geral", "dialog-information-symbolic")
        stack.add_titled_with_icon(self.binaries_tab, "binaries", "Binários", "view-list-symbolic")
        stack.add_titled_with_icon(self.catalog_tab, "catalog", "Capabilities", "system-search-symbolic")
        stack.add_titled_with_icon(self.about_tab, "about", "Sobre", "help-about-symbolic")

        switcher = Adw.ViewSwitcher()
        switcher.set_stack(stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)

        header = Adw.HeaderBar()
        header.set_title_widget(switcher)

        self.toolbar = Adw.ToolbarView()
        self.toolbar.add_top_bar(header)
        if WRAPPED_PACKAGES:
            self.toolbar.add_top_bar(_make_pkg_badges_bar())
        self.toolbar.set_content(stack)

    def _on_scan_done(self, binaries: list[BinaryWithCaps]) -> None:
        self.binaries = binaries
        self.binaries_tab.refresh(binaries)


def build_content() -> Gtk.Widget:
    ctrl = _CapsContent()
    ctrl.toolbar._controller = ctrl  # type: ignore[attr-defined]
    return ctrl.toolbar


class VigiaCapsWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("Capabilities Inspector")
        self.set_default_size(960, 720)
        self.set_content(build_content())
