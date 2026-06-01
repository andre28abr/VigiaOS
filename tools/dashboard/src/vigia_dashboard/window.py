"""Janela principal — orquestra 6 tabs (v0.4: +Rede).

Visao Geral + Recursos + Processos + Rede + Alertas + Sobre.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from . import WRAPPED_PACKAGES
from .tabs import (
    AboutTab,
    AlertsTab,
    NetworkTab,
    OverviewTab,
    ProcessesTab,
    ResourcesTab,
)


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
    """Constroi header + viewstack das 5 tabs.

    PERF v0.2.1: lazy tabs. As 4 tabs visuais (Overview, Resources,
    Processes, About) sao construidas APENAS quando o user navega
    para elas pela primeira vez. Antes, todas 5 eram instanciadas
    no startup (~300+ widgets + 4 GLib.timeouts + Cairo charts) —
    quando o user so vai ver Overview, gastava ~80% de memoria
    desperdicada.

    Excecao: AlertsTab e' construida eager porque precisa rodar em
    background para detectar disparos mesmo quando user esta em
    outra tab.

    Tambem conecta notify::visible-child para pausar timers de tabs
    invisiveis (sem destruir widgets — pause_tick/resume_tick).
    """
    # ------------------------------------------------------------
    # Holders vazios — Adw.ViewStack precisa de widgets reais para
    # `add_titled_with_icon`. Usamos Gtk.Box como placeholder; quando
    # a tab for visitada, construimos o widget real e append nele.
    # ------------------------------------------------------------
    overview_holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    resources_holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    processes_holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    network_holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    about_holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

    # AlertsTab e' eager — precisa rodar em background sempre
    alerts_tab = AlertsTab()

    stack = Adw.ViewStack()
    stack.add_titled_with_icon(overview_holder, "overview", "Visão Geral", "view-grid-symbolic")
    stack.add_titled_with_icon(resources_holder, "resources", "Recursos", "view-statistics-symbolic")
    stack.add_titled_with_icon(processes_holder, "processes", "Processos", "view-list-symbolic")
    stack.add_titled_with_icon(network_holder, "network", "Rede", "network-wireless-symbolic")
    stack.add_titled_with_icon(alerts_tab, "alerts", "Alertas", "dialog-warning-symbolic")
    stack.add_titled_with_icon(about_holder, "about", "Sobre", "help-about-symbolic")

    # State: tabs reais construidas. None = ainda nao construida.
    tabs: dict[str, object] = {
        "overview": None,
        "resources": None,
        "processes": None,
        "network": None,
        "alerts": alerts_tab,  # ja construida
        "about": None,
    }

    holders = {
        "overview": overview_holder,
        "resources": resources_holder,
        "processes": processes_holder,
        "network": network_holder,
        "about": about_holder,
    }

    constructors = {
        "overview": OverviewTab,
        "resources": ResourcesTab,
        "processes": ProcessesTab,
        "network": NetworkTab,
        "about": AboutTab,
    }

    def _build_if_needed(name: str) -> object | None:
        """Constroi a tab se ainda nao foi, retorna o widget."""
        if tabs[name] is not None:
            return tabs[name]
        ctor = constructors.get(name)
        if ctor is None:
            return None
        widget = ctor()
        holders[name].append(widget)
        tabs[name] = widget
        return widget

    def _on_visible_child_changed(stk, _pspec):
        visible_name = stk.get_visible_child_name()
        if visible_name is None:
            return
        # Constroi a tab visivel sob demanda
        _build_if_needed(visible_name)
        # Pause/resume timers das tabs ja construidas
        for name, tab in tabs.items():
            if tab is None:
                continue
            if name == visible_name:
                if hasattr(tab, "resume_tick"):
                    tab.resume_tick()
            elif name != "alerts":  # Alerts sempre ativo
                if hasattr(tab, "pause_tick"):
                    tab.pause_tick()

    stack.connect("notify::visible-child", _on_visible_child_changed)

    # Constroi Overview imediatamente (tab default — user ve ela primeiro)
    _build_if_needed("overview")

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

    # PERF: quando o dashboard INTEIRO fica invisivel (Hub minimiza pra bandeja
    # ou troca de tool), o notify::visible-child interno NAO dispara — entao os
    # timers da tab visivel (Overview 1Hz iterando todos os PIDs, etc.) seguiam
    # sondando /proc e /sys 24/7. Conectamos map/unmap no root pra pausar as
    # tabs VISUAIS (a AlertsTab segue rodando — e' o monitor de background, por
    # design). Padrao espelhado da NetMon (connections.py:139).
    def _pause_visual_tabs() -> None:
        for name, tab in tabs.items():
            if tab is not None and name != "alerts" and hasattr(tab, "pause_tick"):
                tab.pause_tick()

    def _resume_visible_tab() -> None:
        vis = stack.get_visible_child_name()
        tab = tabs.get(vis) if vis else None
        if tab is not None and vis != "alerts" and hasattr(tab, "resume_tick"):
            tab.resume_tick()

    toolbar.connect("map", lambda _w: _resume_visible_tab())
    toolbar.connect("unmap", lambda _w: _pause_visual_tabs())
    return toolbar


class VigiaDashboardWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("Monitor do Sistema")
        self.set_default_size(1080, 760)
        self.set_content(build_content())
