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

from vigia_common.platform import install_hint


class OverviewTab(Adw.Bin):
    """Tab principal: hardening index + acao de auditoria."""

    def __init__(self, on_audit_done: Callable[[], None]) -> None:
        super().__init__()
        self._on_audit_done = on_audit_done
        self._running = False
        self._pulse_id: int | None = None

        # Cleanup ao destruir (memory leak fix do GLib.timeout)
        self.connect("destroy", self._on_destroy)

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

        self._row_warnings = Adw.ActionRow(title="Warnings (críticas)")
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

        self._row_tests_skipped = Adw.ActionRow(title="Tests pulados (skipped)")
        self._row_tests_skipped.set_subtitle(
            "Lynis pula testes que não se aplicam ao sistema. Esperado "
            "em Silverblue (alguns checks assumem dnf, /usr mutável)."
        )
        self._row_tests_skipped.add_css_class("property")
        self._tests_skipped_count = Gtk.Label(label="—")
        self._tests_skipped_count.add_css_class("monospace")
        self._row_tests_skipped.add_suffix(self._tests_skipped_count)

        self._row_last_run = Adw.ActionRow(title="Última execução")
        self._row_last_run.add_css_class("property")
        self._last_run_label = Gtk.Label(label="Nunca")
        self._last_run_label.add_css_class("monospace")
        self._row_last_run.add_suffix(self._last_run_label)

        self._stats_group.add(self._row_warnings)
        self._stats_group.add(self._row_suggestions)
        self._stats_group.add(self._row_tests)
        self._stats_group.add(self._row_tests_skipped)
        self._stats_group.add(self._row_last_run)

        # Banner de contexto (escondido por padrao). Aparece em casos
        # tipo "Lynis rodou mas nao gerou hardening_index" ou
        # "% alto de tests skipped — esperado em Silverblue".
        self._context_banner = Adw.Banner()
        self._context_banner.set_revealed(False)
        self._context_banner.set_title("")

        # ---- Action group ---- #
        self._action_group = Adw.PreferencesGroup()
        self._action_group.set_margin_top(24)
        self._action_group.set_title("Auditoria")
        self._action_group.set_description(
            "Lynis examina ~250 controles de segurança (kernel, boot, "
            "permissões, autenticação, rede, MAC). Precisa de root."
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
        self._progress_label = Gtk.Label(label="Lynis em execução... pode levar alguns minutos.")
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
        outer.append(self._context_banner)
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
        has_data = report.has_data()
        self._warnings_count.set_label(str(len(report.warnings)) if has_data else "—")
        self._suggestions_count.set_label(str(len(report.suggestions)) if has_data else "—")
        self._tests_count.set_label(str(report.tests_executed) if has_data else "—")
        self._tests_skipped_count.set_label(
            str(report.tests_skipped) if has_data else "—"
        )
        self._last_run_label.set_label(format_age(report_age_minutes()))

        # Banner de contexto
        self._update_context_banner(report)

    def _update_context_banner(self, report: LynisReport) -> None:
        """Decide se mostra banner explicativo e qual mensagem."""
        for cls in ("warning", "error"):
            self._context_banner.remove_css_class(cls)

        if not report.has_data():
            self._context_banner.set_revealed(False)
            return

        total_warn_sug = len(report.warnings) + len(report.suggestions)

        # Caso 1: rodou mas nao gerou hardening_index — bug ou parser falhou
        if report.hardening_index is None and report.tests_executed > 0:
            self._context_banner.set_title(
                "Lynis rodou mas não gerou Hardening Index. "
                "Verifique /var/log/lynis-report.dat manualmente."
            )
            self._context_banner.add_css_class("error")
            self._context_banner.set_revealed(True)
            return

        # Caso 2: rodou, gerou indice, mas zero findings — pode ser normal
        # ou parser nao pegou
        if report.hardening_index is not None and total_warn_sug == 0:
            self._context_banner.set_title(
                "Lynis não encontrou warnings nem suggestions. "
                "Pode ser sistema bem configurado OU testes que não se "
                "aplicam (esperado em Silverblue)."
            )
            self._context_banner.add_css_class("warning")
            self._context_banner.set_revealed(True)
            return

        # Caso 3: muitos tests skipped (>30%) — Silverblue tipico
        total = report.tests_executed + report.tests_skipped
        if total > 0:
            skip_ratio = report.tests_skipped / total
            if skip_ratio > 0.3:
                pct = int(skip_ratio * 100)
                self._context_banner.set_title(
                    f"{report.tests_skipped} testes pulados ({pct}% do total). "
                    "Comum em Silverblue: alguns checks assumem dnf ou "
                    "/usr mutável — irrelevantes em sistema atômico."
                )
                self._context_banner.set_revealed(True)
                return

        # Sem caso especial — esconde
        self._context_banner.set_revealed(False)

    # ============================================================
    # Audit run (threading + GLib.idle_add)
    # ============================================================

    def _on_audit_clicked(self, _btn: Gtk.Button) -> None:
        if self._running:
            return
        if not lynis_installed():
            show_error(
                self,
                "Lynis não instalado",
                "O pacote 'lynis' não foi encontrado. Instale:\n\n"
                + install_hint("lynis"),
            )
            return

        self._set_running(True)
        threading.Thread(target=self._audit_worker, daemon=True).start()

    def _audit_worker(self) -> None:
        try:
            ok, err = run_audit_blocking()
        except Exception as e:  # pylint: disable=broad-except
            ok, err = False, f"Excecao no worker: {e}"
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

    def _on_destroy(self, *_args) -> None:
        """Cleanup: para o GLib.timeout do pulse bar (memory leak fix)."""
        if self._pulse_id is not None:
            try:
                GLib.source_remove(self._pulse_id)
            except Exception:  # pylint: disable=broad-except
                pass
            self._pulse_id = None
