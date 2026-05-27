"""Janela principal — 2 tabs (Catalogo + Pendentes).

Suporta modo standalone (VigiaInstallerWindow) e embedded (build_content()).
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from . import WRAPPED_PACKAGES
from .tabs import AboutTab, BrowseTab, ExtensionsTab, PendingTab


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


class _InstallerContent:
    def __init__(self) -> None:
        self.pending = PendingTab(on_changed=lambda: None)
        self.browse = BrowseTab(on_changed=self._on_browse_changed)
        self.extensions = ExtensionsTab()
        self.about = AboutTab()

        stack = Adw.ViewStack()
        stack.add_titled_with_icon(self.browse, "browse", "Catalogo", "package-x-generic-symbolic")
        stack.add_titled_with_icon(self.pending, "pending", "Pendentes", "view-refresh-symbolic")
        stack.add_titled_with_icon(self.extensions, "extensions", "Extensoes", "web-browser-symbolic")
        stack.add_titled_with_icon(self.about, "about", "Sobre", "help-about-symbolic")

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

    def _on_browse_changed(self) -> None:
        """Apos install/uninstall, atualiza tab Pendentes."""
        self.pending.refresh()


def build_content() -> Gtk.Widget:
    ctrl = _InstallerContent()
    ctrl.toolbar._controller = ctrl  # type: ignore[attr-defined]
    return ctrl.toolbar


class VigiaInstallerWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("Tool Installer")
        self.set_default_size(900, 720)
        self.set_content(build_content())
