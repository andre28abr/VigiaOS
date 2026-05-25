"""Janela principal — orquestra 2 tabs (Gerar + Biblioteca).

Suporta modo standalone (VigiaReportsWindow) e embedded (build_content()).
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from . import WRAPPED_PACKAGES
from .tabs import AboutTab, GenerateTab, LibraryTab


def _make_pkg_badges() -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
    box.set_valign(Gtk.Align.CENTER)
    box.set_margin_end(8)
    for pkg in WRAPPED_PACKAGES:
        lbl = Gtk.Label(label=pkg)
        lbl.add_css_class("monospace")
        lbl.add_css_class("caption")
        lbl.add_css_class("dim-label")
        box.append(lbl)
    return box


class _ReportsContent:
    def __init__(self) -> None:
        self.library = LibraryTab()
        self.generate = GenerateTab(on_report_generated=self.library.refresh)
        self.about = AboutTab()

        stack = Adw.ViewStack()
        stack.add_titled_with_icon(self.generate, "generate", "Gerar", "document-new-symbolic")
        stack.add_titled_with_icon(self.library, "library", "Biblioteca", "view-list-symbolic")
        stack.add_titled_with_icon(self.about, "about", "Sobre", "help-about-symbolic")

        switcher = Adw.ViewSwitcher()
        switcher.set_stack(stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)

        header = Adw.HeaderBar()
        header.set_title_widget(switcher)
        if WRAPPED_PACKAGES:
            header.pack_end(_make_pkg_badges())

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
