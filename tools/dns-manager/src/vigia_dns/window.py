"""Janela principal — 3 tabs (Status + Provedores + Sobre)."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from . import WRAPPED_PACKAGES
from .tabs import AboutTab, ResolversTab, StatusTab


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


def build_content() -> Gtk.Widget:
    status_tab = StatusTab()
    resolvers_tab = ResolversTab()
    about_tab = AboutTab()

    stack = Adw.ViewStack()
    stack.add_titled_with_icon(status_tab, "status", "Status", "dialog-information-symbolic")
    stack.add_titled_with_icon(resolvers_tab, "resolvers", "Provedores", "view-list-symbolic")
    stack.add_titled_with_icon(about_tab, "about", "Sobre", "help-about-symbolic")

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


class VigiaDnsWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("DNS Manager")
        self.set_default_size(900, 720)
        self.set_content(build_content())
