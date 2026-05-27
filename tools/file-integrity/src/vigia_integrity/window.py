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
from .tabs import (
    AboutTab,
    BaselineTab,
    ChangesTab,
    HashTab,
    StatusTab,
    VerifyTab,
)


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


class _IntegrityContent:
    def __init__(self) -> None:
        self.changes = ChangesTab()
        self.about = AboutTab()
        self.status = StatusTab(
            on_check_done=self._on_check_done,
            on_profile_changed=self._on_profile_changed,
        )
        # v0.2.0: tabs vindas do merge com Hash Tools
        self.hash_tab = HashTab()
        self.verify = VerifyTab()
        self.baseline = BaselineTab()

        stack = Adw.ViewStack()
        # AIDE (escala sistema, requer root)
        stack.add_titled_with_icon(self.status, "status", "Status (AIDE)", "dialog-information-symbolic")
        stack.add_titled_with_icon(self.changes, "changes", "Mudancas (AIDE)", "view-list-symbolic")
        # Hash ad-hoc (escala arquivo/diretorio, sem root)
        stack.add_titled_with_icon(self.hash_tab, "hash", "Hash", "edit-find-symbolic")
        stack.add_titled_with_icon(self.verify, "verify", "Verificar", "object-select-symbolic")
        stack.add_titled_with_icon(self.baseline, "baseline", "Baseline", "folder-symbolic")
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
