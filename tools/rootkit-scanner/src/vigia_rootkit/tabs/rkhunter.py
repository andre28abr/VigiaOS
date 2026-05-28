"""Tab Rootkit Hunter (rkhunter) — scan completo.

Estrutura identica a chkrootkit.py mas adaptada pra rkhunter
(que demora mais e tem 200+ checks).
"""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Pango", "1.0")

from gi.repository import Adw, GLib, Gtk, Pango  # noqa: E402

from .. import backend
from ._helpers import make_clamp, show_error, show_info


HEADER_DESC = (
    "<b>Rootkit Hunter (rkhunter)</b> roda 200+ checks: rootkits, "
    "backdoors, integridade de binarios via hash, permissoes, configs "
    "SSH, processos escondidos. Mais detalhado que chkrootkit. "
    "Demora 2-5 minutos."
)


class RkhunterTab(Adw.Bin):
    """Aba Rootkit Hunter — mesma estrutura da chkrootkit.py."""

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._stop_requested = False
        self._destroyed = False

        self._banner = Adw.Banner()
        self._banner.set_revealed(False)

        header_lbl = Gtk.Label(label="Rootkit Hunter")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(6)

        header_desc = Gtk.Label()
        header_desc.set_markup(HEADER_DESC)
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(20)

        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_margin_top(16)
        action_box.set_margin_bottom(12)

        self._run_btn = Gtk.Button(label="Iniciar scan")
        self._run_btn.add_css_class("suggested-action")
        self._run_btn.connect("clicked", self._on_scan_clicked)
        action_box.append(self._run_btn)

        self._stop_btn = Gtk.Button(label="Parar")
        self._stop_btn.add_css_class("destructive-action")
        self._stop_btn.set_sensitive(False)
        self._stop_btn.connect("clicked", lambda _b: self._request_stop())
        action_box.append(self._stop_btn)

        self._status_label = Gtk.Label(label="Pronto.")
        self._status_label.add_css_class("dim-label")
        self._status_label.set_halign(Gtk.Align.START)
        self._status_label.set_margin_top(4)
        self._status_label.set_margin_bottom(16)
        self._status_label.set_wrap(True)
        self._status_label.set_xalign(0)

        kpis_group = Adw.PreferencesGroup()
        kpis_group.set_margin_top(8)
        kpis_group.set_title("Estatisticas")

        self._row_tests = Adw.ActionRow(title="Testes rodados")
        self._row_tests.add_css_class("property")
        self._lbl_tests = Gtk.Label(label="—")
        self._lbl_tests.add_css_class("monospace")
        self._row_tests.add_suffix(self._lbl_tests)
        kpis_group.add(self._row_tests)

        self._row_warn = Adw.ActionRow(title="Warnings")
        self._row_warn.add_css_class("property")
        self._lbl_warn = Gtk.Label(label="—")
        self._lbl_warn.add_css_class("monospace")
        self._row_warn.add_suffix(self._lbl_warn)
        kpis_group.add(self._row_warn)

        self._row_inf = Adw.ActionRow(title="Infectados")
        self._row_inf.add_css_class("property")
        self._lbl_inf = Gtk.Label(label="—")
        self._lbl_inf.add_css_class("monospace")
        self._row_inf.add_suffix(self._lbl_inf)
        kpis_group.add(self._row_inf)

        log_expander = Adw.ExpanderRow()
        log_expander.set_title("Saida do scan")
        log_expander.set_subtitle("Output bruto (streaming em tempo real)")
        log_expander.set_expanded(True)

        self._log_view = Gtk.TextView()
        self._log_view.set_editable(False)
        self._log_view.set_cursor_visible(False)
        self._log_view.set_monospace(True)
        self._log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._log_view.set_top_margin(8)
        self._log_view.set_bottom_margin(8)
        self._log_view.set_left_margin(8)
        self._log_view.set_right_margin(8)
        self._log_buf = self._log_view.get_buffer()

        self._tag_warning = self._log_buf.create_tag(
            "warning", foreground="#fbbf24", weight=Pango.Weight.BOLD,
        )
        self._tag_infected = self._log_buf.create_tag(
            "infected", foreground="#f87171", weight=Pango.Weight.BOLD,
        )

        log_scrolled = Gtk.ScrolledWindow()
        log_scrolled.set_min_content_height(240)
        log_scrolled.set_max_content_height(380)
        log_scrolled.set_child(self._log_view)

        log_row = Adw.ActionRow()
        log_row.set_child(log_scrolled)
        log_row.set_activatable(False)
        log_expander.add_row(log_row)

        log_group = Adw.PreferencesGroup()
        log_group.set_margin_top(16)
        log_group.add(log_expander)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_top(24)
        inner.set_margin_bottom(28)
        inner.set_margin_start(28)
        inner.set_margin_end(28)
        inner.append(header_lbl)
        inner.append(header_desc)
        inner.append(action_box)
        inner.append(self._status_label)
        inner.append(kpis_group)
        inner.append(log_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(inner))

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.append(self._banner)
        outer.append(scrolled)
        self.set_child(outer)

        self.connect("destroy", self._on_destroy)
        self.refresh()

    def _on_destroy(self, *_a) -> None:
        self._destroyed = True

    def refresh(self) -> None:
        if not backend.rkhunter_installed():
            self._banner.set_title(
                "rkhunter nao instalado. Instale via Vigia Tool Installer "
                "(pacote rkhunter)."
            )
            self._banner.set_revealed(True)
            self._run_btn.set_sensitive(False)
        else:
            self._banner.set_revealed(False)
            self._run_btn.set_sensitive(True)

    def _on_scan_clicked(self, _btn) -> None:
        if self._running:
            return

        dlg = Adw.AlertDialog(
            heading="Iniciar scan Rootkit Hunter?",
            body=(
                "rkhunter vai rodar como root via pkexec.\n\n"
                "Tempo aproximado: 2-5 minutos.\n\n"
                "Voce pode parar a qualquer momento. Sera pedida senha admin."
            ),
        )
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("start", "Iniciar")
        dlg.set_response_appearance("start", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("cancel")
        dlg.connect("response", self._on_scan_confirmed)
        dlg.present(self.get_root())

    def _on_scan_confirmed(self, _dlg, response: str) -> None:
        if response != "start":
            return
        self._start_scan()

    def _start_scan(self) -> None:
        self._running = True
        self._stop_requested = False
        self._run_btn.set_sensitive(False)
        self._stop_btn.set_sensitive(True)
        self._log_buf.set_text("")
        self._lbl_tests.set_label("0")
        self._lbl_warn.set_label("0")
        self._lbl_inf.set_label("0")
        self._set_label_color(self._lbl_warn, "")
        self._set_label_color(self._lbl_inf, "")
        self._status_label.set_label("Iniciando scan...")

        backend.scan_rkhunter_async(
            on_line=self._on_scan_line,
            on_done=self._on_scan_done,
            stop_flag=lambda: self._stop_requested,
        )

    def _request_stop(self) -> None:
        self._stop_requested = True
        self._status_label.set_label("Cancelando scan...")
        self._append_line("\n[Vigia] Cancelando scan...")

    def _on_scan_line(self, line: str) -> None:
        GLib.idle_add(self._append_line, line)

    def _append_line(self, line: str) -> bool:
        if self._destroyed:
            return False
        end_iter = self._log_buf.get_end_iter()
        tag = None
        l = line.lower()
        if "infected" in l and "not infected" not in l:
            tag = self._tag_infected
        elif "warning" in l or "vulnerable" in l:
            tag = self._tag_warning

        if tag is not None:
            self._log_buf.insert_with_tags(end_iter, line + "\n", tag)
        else:
            self._log_buf.insert(end_iter, line + "\n")

        mark = self._log_buf.create_mark(None, self._log_buf.get_end_iter(), False)
        self._log_view.scroll_to_mark(mark, 0, False, 0, 0)
        self._log_buf.delete_mark(mark)

        if line.strip().startswith("Checking"):
            try:
                current = int(self._lbl_tests.get_label() or "0")
                self._lbl_tests.set_label(str(current + 1))
            except (ValueError, TypeError):
                pass
        return False

    def _on_scan_done(self, result: backend.ScanResult) -> None:
        GLib.idle_add(self._on_scan_done_ui, result)

    def _on_scan_done_ui(self, result: backend.ScanResult) -> bool:
        if self._destroyed:
            return False
        self._running = False
        self._run_btn.set_sensitive(True)
        self._stop_btn.set_sensitive(False)

        self._lbl_tests.set_label(str(result.tests_run))
        self._lbl_warn.set_label(str(result.warnings_count))
        self._lbl_inf.set_label(str(result.infected_count))

        if result.warnings_count > 0:
            self._set_label_color(self._lbl_warn, "warning")
        if result.infected_count > 0:
            self._set_label_color(self._lbl_inf, "error")

        if result.cancelled:
            self._status_label.set_label("Scan cancelado pelo usuario.")
            show_info(self, "Scan cancelado", "Scan interrompido pelo usuario.")
        elif result.error:
            self._status_label.set_label(f"Erro: {result.error[:120]}")
            show_error(self, "Erro no scan", result.error)
        elif result.infected_count > 0:
            self._status_label.set_label(
                f"Scan completo: {result.infected_count} infectado(s)."
            )
            show_error(
                self,
                f"rkhunter: {result.infected_count} infectado(s)",
                "Revise a saida do scan e tome acoes apropriadas. "
                "Resultado salvo no Historico.",
            )
            notify_if_unfocused(
                f"rkhunter: {result.infected_count} infectado(s)",
                "Possivel rootkit detectado. Abra o Vigia pra revisar.",
                notif_id="vigia-rootkit-rkhunter",
                priority=PRIORITY_HIGH,
            )
        elif result.warnings_count > 0:
            self._status_label.set_label(
                f"Scan completo: {result.warnings_count} warning(s)."
            )
            show_info(
                self,
                f"rkhunter: {result.warnings_count} warning(s)",
                "Sistema parece OK mas vale revisar. Resultado salvo no Historico.",
            )
            notify_if_unfocused(
                f"rkhunter: {result.warnings_count} warning(s)",
                "Scan concluido — vale revisar os avisos no Vigia.",
                notif_id="vigia-rootkit-rkhunter",
            )
        else:
            self._status_label.set_label("Scan completo: nenhum sinal detectado.")
            show_info(
                self,
                "rkhunter: limpo",
                "Nenhum sinal de rootkit detectado. Resultado salvo no Historico.",
            )
            notify_if_unfocused(
                "rkhunter: limpo",
                "Nenhum sinal de rootkit detectado.",
                notif_id="vigia-rootkit-rkhunter",
            )
        return False

    @staticmethod
    def _set_label_color(label: Gtk.Label, level: str) -> None:
        for cls in ("success", "warning", "error"):
            label.remove_css_class(cls)
        if level:
            label.add_css_class(level)
