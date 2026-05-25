"""Janela principal — orquestra 3 tabs (Status + Mudancas + Sobre).

Suporta modo standalone (VigiaIntegrityWindow) e embedded (build_content()).
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from . import WRAPPED_PACKAGES
from .backend import CheckResult
from .tabs import AboutTab, ChangesTab, StatusTab


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


class _IntegrityContent:
    def __init__(self) -> None:
        self.changes = ChangesTab()
        self.about = AboutTab()
        self.status = StatusTab(
            on_check_done=self._on_check_done,
            on_profile_changed=self._on_profile_changed,
        )

        stack = Adw.ViewStack()
        stack.add_titled_with_icon(self.status, "status", "Status", "dialog-information-symbolic")
        stack.add_titled_with_icon(self.changes, "changes", "Mudancas", "view-list-symbolic")
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

    def _on_check_done(self, result: CheckResult) -> None:
        self.changes.refresh(result.changes)

    def _on_profile_changed(self) -> None:
        """Quando o perfil AIDE muda (aplica/remove), atualiza tabs que
        mostram info do perfil (Sobre tem indicador read-only)."""
        self.about.refresh()


def build_content() -> Gtk.Widget:
    ctrl = _IntegrityContent()
    ctrl.toolbar._controller = ctrl  # type: ignore[attr-defined]
    return ctrl.toolbar


class VigiaIntegrityWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("File Integrity")
        self.set_default_size(900, 720)
        self.set_content(build_content())
