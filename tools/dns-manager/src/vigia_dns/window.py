"""Janela principal — 3 tabs (Status, Provedores, Sobre).

v0.4.0: enxugado. Removido Blocklists e Stats — bloqueio de ads/trackers
e' feito melhor por extensoes de navegador (uBlock Origin etc.), que
ficam disponiveis via Vigia Tool Installer.

DNS Manager agora foca em: DNS encriptado (DoH/DoT/DNSCrypt) com
catalogo de servers no-logs + DNSSEC.
"""

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

    # v0.4.0: apos Ativar/Restaurar dnscrypt-proxy, refresca Provedores
    def _on_activation_changed() -> None:
        try:
            resolvers_tab.refresh()
        except Exception:  # pylint: disable=broad-except
            pass

    status_tab.on_activation_changed = _on_activation_changed

    # Refresh on-activation: trocar de tab refresca ela
    def _on_visible_child_changed(stk, _pspec):
        visible_name = stk.get_visible_child_name()
        tab_map = {
            "status": status_tab,
            "resolvers": resolvers_tab,
        }
        tab = tab_map.get(visible_name)
        if tab is not None and hasattr(tab, "refresh"):
            try:
                tab.refresh()
            except Exception:  # pylint: disable=broad-except
                pass

    stack.connect("notify::visible-child", _on_visible_child_changed)

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
