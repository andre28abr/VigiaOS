"""Tab Overview: Hardening Index + botao 'Executar auditoria'."""

from __future__ import annotations

import threading
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from ..backend import (
    LynisReport,
    format_age,
    lynis_installed,
    report_age_minutes,
    run_audit_blocking,
)
from ._helpers import make_clamp, severity_css_class, severity_label, show_error


class OverviewTab(Adw.Bin):
    """Tab principal: hardening index + acao de auditoria."""

    def __init__(self, on_audit_done: Callable[[], None]) -> None:
        super().__init__()
        self._on_audit_done = on_audit_done
        self._running = False

        # ---- Hero box ---- #
        self._hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._hero.set_halign(Gtk.Align.CENTER)
        self._hero.set_margin_top(40)
        self._hero.set_margin_bottom(20)

        self._score_label = Gtk.Label(label="—")
        self._score_label.add_css_class("title-1")
        self._score_label.set_halign(Gtk.Align.CENTER)
        self._score_label.add_css_class("dim-label")

        self._score_suffix = Gtk.Label(label="de 100")
        self._score_suffix.add_css_class("title-4")
        self._score_suffix.add_css_class("dim-label")
        self._score_suffix.set_halign(Gtk.Align.CENTER)

        self._severity_label = Gtk.Label(label="Sem dados")
        self._severity_label.add_css_class("title-3")
        self._severity_label.set_halign(Gtk.Align.CENTER)
        self._severity_label.set_margin_top(8)

        # Progress bar (representa o score)
        self._score_bar = Gtk.ProgressBar()
        self._score_bar.set_fraction(0)
        self._score_bar.set_size_request(360, -1)
        self._score_bar.set_margin_top(16)
        self._score_bar.set_halign(Gtk.Align.CENTER)

        self._hero.append(self._score_label)
        self._hero.append(self._score_suffix)
        self._hero.append(self._severity_label)
        self._hero.append(self._score_bar)

        # ---- Stats group ---- #
        self._stats_group = Adw.PreferencesGroup()
        self._stats_group.set_title("Resumo da auditoria")

        self._row_warnings = Adw.ActionRow(title="Warnings (criticas)")
        self._row_warnings.add_css_class("property")
        self._warnings_count = Gtk.Label(label="—")
        self._warnings_count.add_css_class("monospace")
        self._row_warnings.add_suffix(self._warnings_count)

        self._row_suggestions = Adw.ActionRow(title="Suggestions (melhorias)")
        self._row_suggestions.add_css_class("property")
        self._suggestions_count = Gtk.Label(label="—")
        self._suggestions_count.add_css_class("monospace")
        self._row_suggestions.add_suffix(self._suggestions_count)

        self._row_tests = Adw.ActionRow(title="Tests executados")
        self._row_tests.add_css_class("property")
        self._tests_count = Gtk.Label(label="—")
        self._tests_count.add_css_class("monospace")
        self._row_tests.add_suffix(self._tests_count)

        self._row_last_run = Adw.ActionRow(title="Ultima execucao")
        self._row_last_run.add_css_class("property")
        self._last_run_label = Gtk.Label(label="Nunca")
        self._last_run_label.add_css_class("monospace")
        self._row_last_run.add_suffix(self._last_run_label)

        self._stats_group.add(self._row_warnings)
        self._stats_group.add(self._row_suggestions)
        self._stats_group.add(self._row_tests)
        self._stats_group.add(self._row_last_run)

        # ---- Action group ---- #
        self._action_group = Adw.PreferencesGroup()
        self._action_group.set_title("Auditoria")
        self._action_group.set_description(
            "Lynis examina ~250 controles de seguranca (kernel, boot, "
            "permissoes, autenticacao, rede, MAC). Precisa de root."
        )

        action_row = Adw.ActionRow(title="Executar auditoria completa")
        action_row.set_subtitle("Roda lynis audit system via pkexec (2 a 5 min)")
        self._audit_btn = Gtk.Button(label="Executar")
        self._audit_btn.add_css_class("suggested-action")
        self._audit_btn.set_valign(Gtk.Align.CENTER)
        self._audit_btn.connect("clicked", self._on_audit_clicked)
        action_row.add_suffix(self._audit_btn)
        self._action_group.add(action_row)

        # Progress (escondido por padrao)
        self._progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._progress_box.set_visible(False)
        self._progress_box.set_margin_top(8)
        self._progress_label = Gtk.Label(label="Lynis em execucao... pode levar alguns minutos.")
        self._progress_label.add_css_class("dim-label")
        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.set_pulse_step(0.1)
        self._progress_box.append(self._progress_label)
        self._progress_box.append(self._progress_bar)

        # ---- Layout ---- #
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        outer.set_margin_top(24)
        outer.set_margin_bottom(32)
        outer.set_margin_start(20)
        outer.set_margin_end(20)
        outer.append(self._hero)
        outer.append(self._stats_group)
        outer.append(self._action_group)
        outer.append(self._progress_box)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

    # ============================================================
    # Refresh com novo report
    # ============================================================

    def refresh(self, report: LynisReport) -> None:
        score = report.hardening_index

        # Score label
        if score is not None:
            self._score_label.set_label(str(score))
            for cls in ("success", "warning", "error", "dim-label"):
                self._score_label.remove_css_class(cls)
            self._score_label.add_css_class(severity_css_class(score))
            self._score_bar.set_fraction(max(0.0, min(1.0, score / 100.0)))
        else:
            self._score_label.set_label("—")
            self._score_bar.set_fraction(0)

        # Severity
        self._severity_label.set_label(severity_label(score))
        for cls in ("success", "warning", "error", "dim-label"):
            self._severity_label.remove_css_class(cls)
        self._severity_label.add_css_class(severity_css_class(score))

        # Stats
        self._warnings_count.set_label(str(len(report.warnings)) if report.has_data() else "—")
        self._suggestions_count.set_label(str(len(report.suggestions)) if report.has_data() else "—")
        self._tests_count.set_label(str(report.tests_executed) if report.has_data() else "—")
        self._last_run_label.set_label(format_age(report_age_minutes()))

    # ============================================================
    # Audit run (threading + GLib.idle_add)
    # ============================================================

    def _on_audit_clicked(self, _btn: Gtk.Button) -> None:
        if self._running:
            return
        if not lynis_installed():
            show_error(
                self,
                "Lynis nao instalado",
                "O pacote 'lynis' nao foi encontrado. Em Fedora Silverblue:\n\n"
                "rpm-ostree install lynis\nsystemctl reboot",
            )
            return

        self._set_running(True)
        threading.Thread(target=self._audit_worker, daemon=True).start()

    def _audit_worker(self) -> None:
        ok, err = run_audit_blocking()
        GLib.idle_add(self._on_audit_finished, ok, err)

    def _on_audit_finished(self, ok: bool, err: str) -> bool:
        self._set_running(False)
        if not ok:
            show_error(self, "Auditoria falhou", err)
        else:
            self._on_audit_done()
        return False  # GLib.idle_add: nao repete

    def _set_running(self, running: bool) -> None:
        self._running = running
        self._audit_btn.set_sensitive(not running)
        self._audit_btn.set_label("Executando..." if running else "Executar")
        self._progress_box.set_visible(running)
        if running:
            self._pulse_id = GLib.timeout_add(100, self._pulse_tick)
        else:
            pid = getattr(self, "_pulse_id", None)
            if pid is not None:
                GLib.source_remove(pid)
                self._pulse_id = None

    def _pulse_tick(self) -> bool:
        self._progress_bar.pulse()
        return self._running  # continua enquanto running
