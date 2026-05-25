"""Janela principal — 3 tabs (Status + Timeline + Correlations).

Header tem:
- Switch 'Modo admin' (pkexec)
- Botao 'Atualizar' (dispara nova coleta)
- ViewSwitcher das 3 tabs

Suporta modo standalone (VigiaLogGuiWindow) e embedded (build_content()).
"""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from . import backend
from .backend import ActivityBundle
from .tabs import CorrelationsTab, StatusTab, TimelineTab
from .tabs._helpers import show_error


class _LogGuiContent:
    """Controller: state (bundle, running flag) + tabs + header com Admin/Atualizar."""

    def __init__(self) -> None:
        self._bundle = ActivityBundle()
        self._running = False
        self._pulse_id: int | None = None

        self.status = StatusTab()
        self.timeline = TimelineTab()
        self.correlations = CorrelationsTab()

        # ViewStack
        stack = Adw.ViewStack()
        stack.add_titled_with_icon(self.status, "status", "Status", "dialog-information-symbolic")
        stack.add_titled_with_icon(self.timeline, "timeline", "Timeline", "view-list-symbolic")
        stack.add_titled_with_icon(self.correlations, "correlations", "Correlations", "emblem-shared-symbolic")

        switcher = Adw.ViewSwitcher()
        switcher.set_stack(stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)

        # Header
        header = Adw.HeaderBar()
        header.set_title_widget(switcher)

        # Admin switch (left)
        self._admin_switch = Gtk.Switch()
        self._admin_switch.set_valign(Gtk.Align.CENTER)
        self._admin_switch.set_tooltip_text(
            "Modo admin (pkexec) — acessa audit.log e journal do sistema"
        )
        admin_lbl = Gtk.Label(label="Admin")
        admin_lbl.add_css_class("caption-heading")
        admin_lbl.set_valign(Gtk.Align.CENTER)
        admin_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        admin_box.append(admin_lbl)
        admin_box.append(self._admin_switch)
        header.pack_start(admin_box)

        # Refresh button (right)
        self._refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        self._refresh_btn.set_tooltip_text("Coletar eventos novos")
        self._refresh_btn.add_css_class("suggested-action")
        self._refresh_btn.connect("clicked", self._on_refresh_clicked)
        header.pack_end(self._refresh_btn)

        # ProgressBar (osd, escondida)
        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.set_pulse_step(0.1)
        self._progress_bar.set_visible(False)
        self._progress_bar.add_css_class("osd")

        # ToolbarView
        self.toolbar = Adw.ToolbarView()
        self.toolbar.add_top_bar(header)
        self.toolbar.add_top_bar(self._progress_bar)
        self.toolbar.set_content(stack)

    # ============================================================
    # Refresh
    # ============================================================

    def _on_refresh_clicked(self, _btn: Gtk.Button) -> None:
        if self._running:
            return
        elevated = self._admin_switch.get_active()
        sources = sorted(backend.detect_available_sources())
        if not sources:
            show_error(
                self._refresh_btn,
                "Nenhuma fonte disponivel",
                "Nao detectei audit, journal ou fail2ban neste sistema.",
            )
            return

        self._set_running(True)
        threading.Thread(
            target=self._worker,
            args=(sources, elevated),
            daemon=True,
        ).start()

    def _worker(self, sources: list[str], elevated: bool) -> None:
        try:
            bundle = backend.run_bundle(sources=sources, elevated=elevated, limit=500)
        except Exception as e:  # pylint: disable=broad-except
            bundle = ActivityBundle()
            bundle.raw_error = f"Excecao no worker: {e}"
        GLib.idle_add(self._on_done, bundle)

    def _on_done(self, bundle: ActivityBundle) -> bool:
        self._set_running(False)
        if bundle.raw_error:
            show_error(self._refresh_btn, "Falha ao coletar", bundle.raw_error)
            return False
        self._bundle = bundle
        self.status.refresh(bundle)
        self.timeline.refresh(bundle)
        self.correlations.refresh(bundle)
        return False

    def _set_running(self, running: bool) -> None:
        self._running = running
        self._refresh_btn.set_sensitive(not running)
        self._progress_bar.set_visible(running)
        if running:
            self._pulse_id = GLib.timeout_add(100, self._pulse_tick)
        elif self._pulse_id is not None:
            GLib.source_remove(self._pulse_id)
            self._pulse_id = None

    def _pulse_tick(self) -> bool:
        self._progress_bar.pulse()
        return self._running


def build_content() -> Gtk.Widget:
    ctrl = _LogGuiContent()
    ctrl.toolbar._controller = ctrl  # type: ignore[attr-defined]
    return ctrl.toolbar


class VigiaLogGuiWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("Activity Log")
        self.set_default_size(1100, 760)
        self.set_content(build_content())
