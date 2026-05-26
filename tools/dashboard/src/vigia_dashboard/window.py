"""Janela principal — orquestra 5 tabs (v0.2: +Alertas).

Visao Geral + Recursos + Processos + Alertas + Sobre.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from . import WRAPPED_PACKAGES
from .tabs import AboutTab, AlertsTab, OverviewTab, ProcessesTab, ResourcesTab


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

    PERF: connecta notify::visible-child no ViewStack para pausar timers
    de tabs invisiveis. Tabs implementam pause_tick()/resume_tick() que
    chamam GLib.source_remove() e GLib.timeout_add() respectivamente.

    Cuts ~75% da carga de I/O quando usuario ve apenas 1 tab por vez.
    """
    overview_tab = OverviewTab()
    resources_tab = ResourcesTab()
    processes_tab = ProcessesTab()
    alerts_tab = AlertsTab()
    about_tab = AboutTab()

    stack = Adw.ViewStack()
    stack.add_titled_with_icon(overview_tab, "overview", "Visao Geral", "view-grid-symbolic")
    stack.add_titled_with_icon(resources_tab, "resources", "Recursos", "view-statistics-symbolic")
    stack.add_titled_with_icon(processes_tab, "processes", "Processos", "view-list-symbolic")
    stack.add_titled_with_icon(alerts_tab, "alerts", "Alertas", "dialog-warning-symbolic")
    stack.add_titled_with_icon(about_tab, "about", "Sobre", "help-about-symbolic")

    # Map name → widget (para pause/resume baseado no visible-child)
    tabs_by_name = {
        "overview": overview_tab,
        "resources": resources_tab,
        "processes": processes_tab,
        "alerts": alerts_tab,
        "about": about_tab,
    }

    def _on_visible_child_changed(stk, _pspec):
        visible_name = stk.get_visible_child_name()
        for name, tab in tabs_by_name.items():
            if name == visible_name:
                if hasattr(tab, "resume_tick"):
                    tab.resume_tick()
            else:
                if hasattr(tab, "pause_tick"):
                    tab.pause_tick()
        # IMPORTANTE: tab Alertas sempre roda em background (para detectar
        # disparos mesmo quando user nao esta vendo Alertas). Resume forcado:
        if visible_name != "alerts" and hasattr(alerts_tab, "resume_tick"):
            alerts_tab.resume_tick()

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


class VigiaDashboardWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("Dashboard")
        self.set_default_size(1080, 760)
        self.set_content(build_content())
