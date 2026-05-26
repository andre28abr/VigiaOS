"""Janela principal — 5 tabs (v0.2: +Blocklists +Stats).

Status + Provedores + Blocklists + Stats + Sobre.

Blocklists e Stats so sao funcionais com modo avancado ativo
(dnscrypt-proxy). Em modo simples, mostram banner explicativo.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from . import WRAPPED_PACKAGES
from .tabs import AboutTab, BlocklistsTab, ResolversTab, StatsTab, StatusTab


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
    blocklists_tab = BlocklistsTab()
    stats_tab = StatsTab()
    about_tab = AboutTab()

    stack = Adw.ViewStack()
    stack.add_titled_with_icon(status_tab, "status", "Status", "dialog-information-symbolic")
    stack.add_titled_with_icon(resolvers_tab, "resolvers", "Provedores", "view-list-symbolic")
    stack.add_titled_with_icon(blocklists_tab, "blocklists", "Blocklists", "action-unavailable-symbolic")
    stack.add_titled_with_icon(stats_tab, "stats", "Stats", "view-statistics-symbolic")
    stack.add_titled_with_icon(about_tab, "about", "Sobre", "help-about-symbolic")

    # ============================================================
    # Sincronia entre tabs (v0.2.1):
    # Blocklists/Stats dependem do modo (advanced/simple) detectado
    # pelo StatusTab. Sem propagacao, o banner "modo avancado nao esta
    # ativo" ficaria stale apos o user ativar o switch.
    #
    # 2 mecanismos:
    # 1. Callback direto: status_tab.on_mode_changed dispara refresh
    #    imediato em blocklists_tab e stats_tab quando o switch muda
    # 2. Refresh on-activation: trocar para Blocklists/Stats sempre
    #    refresca (catch-all caso o callback falhe ou estado mude
    #    externamente)
    # ============================================================
    def _refresh_mode_dependent_tabs() -> None:
        """Refresh tabs que dependem do modo (advanced/simple)."""
        try:
            blocklists_tab.refresh()
        except Exception:  # pylint: disable=broad-except
            pass
        try:
            stats_tab.refresh()
        except Exception:  # pylint: disable=broad-except
            pass

    status_tab.on_mode_changed = _refresh_mode_dependent_tabs

    def _on_visible_child_changed(stk, _pspec):
        visible_name = stk.get_visible_child_name()
        if visible_name == "blocklists":
            try:
                blocklists_tab.refresh()
            except Exception:  # pylint: disable=broad-except
                pass
        elif visible_name == "stats":
            try:
                stats_tab.refresh()
            except Exception:  # pylint: disable=broad-except
                pass
        elif visible_name == "status":
            try:
                status_tab.refresh()
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
