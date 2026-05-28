"""Widget de scan compartilhado entre chkrootkit e rkhunter tabs.

v0.1.4 — REESCRITO seguindo EXATAMENTE o pattern do Antivirus scan tab
(que funciona sem esticar a janela do Hub). Versoes anteriores (0.1.0
a 0.1.3) tinham widgets que pediam natural size grande, propagando pra
cima da arvore Adw.ViewStack e esticando a janela.

Pattern correto observado no Antivirus:
- KPIs em Adw.PreferencesGroup com 3 Adw.ActionRow (title + valor suffix)
- TextView dentro de Adw.PreferencesGroup > Adw.ExpanderRow > Adw.ActionRow
- Boxes horizontais SEM halign forcado (deixa default = FILL pequeno)
- Banner FORA do clamp (set_revealed(False) padrao)
"""

from __future__ import annotations

import threading
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Pango", "1.0")

from gi.repository import Adw, GLib, Gtk, Pango  # noqa: E402

from .. import backend
from ._helpers import make_clamp, show_error, show_info


class ScanView(Adw.Bin):
    """Widget generico de scan — pattern Antivirus.

    Args:
        scanner_name: 'chkrootkit' ou 'rkhunter'
        scanner_label: display name (ex: 'Rootkit Hunter')
        description: paragrafo curto explicando o scanner
        install_pkg: nome do RPM pra mostrar caso nao instalado
        scan_starter: funcao que dispara o scan async
            assinatura: (on_line, on_done, stop_flag) -> Thread
        installed_checker: funcao que retorna bool
    """

    def __init__(
        self,
        scanner_name: str,
        scanner_label: str,
        description: str,
        install_pkg: str,
        scan_starter: Callable,
        installed_checker: Callable[[], bool],
    ) -> None:
        super().__init__()
        self._scanner_name = scanner_name
        self._scanner_label = scanner_label
        self._install_pkg = install_pkg
        self._scan_starter = scan_starter
        self._installed_checker = installed_checker

        self._running = False
        self._stop_requested = False
        self._destroyed = False

        # ------------------------------------------------------------
        # Banner de estado (nao instalado, etc.)
        # ------------------------------------------------------------
        self._banner = Adw.Banner()
        self._banner.set_revealed(False)

        # ------------------------------------------------------------
        # Header
        # ------------------------------------------------------------
        header_lbl = Gtk.Label(label=scanner_label)
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(6)

        header_desc = Gtk.Label()
        header_desc.set_markup(description)
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(20)

        # ------------------------------------------------------------
        # Run / Stop
        # ------------------------------------------------------------
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_margin_top(16)
        action_box.set_margin_bottom(12)

        self._scan_btn = Gtk.Button(label="Iniciar scan")
        self._scan_btn.add_css_class("suggested-action")
        self._scan_btn.connect("clicked", self._on_scan_clicked)
        action_box.append(self._scan_btn)

        self._stop_btn = Gtk.Button(label="Parar")
        self._stop_btn.add_css_class("destructive-action")
        self._stop_btn.set_sensitive(False)
        self._stop_btn.connect("clicked", self._on_stop_clicked)
        action_box.append(self._stop_btn)

        # Status line
        self._status_label = Gtk.Label(label="Pronto.")
        self._status_label.add_css_class("dim-label")
        self._status_label.set_halign(Gtk.Align.START)
        self._status_label.set_margin_top(4)
        self._status_label.set_margin_bottom(16)
        self._status_label.set_wrap(True)
        self._status_label.set_xalign(0)

        # ------------------------------------------------------------
        # KPIs como PreferencesGroup com 3 ActionRows
        # (substituiu Box horizontal com cards 150x80 que pediam 486px
        # de natural width e esticavam a janela do Hub)
        # ------------------------------------------------------------
        self._kpis_group = Adw.PreferencesGroup()
        self._kpis_group.set_margin_top(8)
        self._kpis_group.set_title("Estatisticas")

        self._row_tests = Adw.ActionRow(title="Testes rodados")
        self._row_tests.add_css_class("property")
        self._lbl_tests = Gtk.Label(label="—")
        self._lbl_tests.add_css_class("monospace")
        self._row_tests.add_suffix(self._lbl_tests)
        self._kpis_group.add(self._row_tests)

        self._row_warn = Adw.ActionRow(title="Warnings")
        self._row_warn.add_css_class("property")
        self._lbl_warn = Gtk.Label(label="—")
        self._lbl_warn.add_css_class("monospace")
        self._row_warn.add_suffix(self._lbl_warn)
        self._kpis_group.add(self._row_warn)

        self._row_inf = Adw.ActionRow(title="Infectados")
        self._row_inf.add_css_class("property")
        self._lbl_inf = Gtk.Label(label="—")
        self._lbl_inf.add_css_class("monospace")
        self._row_inf.add_suffix(self._lbl_inf)
        self._kpis_group.add(self._row_inf)

        # ------------------------------------------------------------
        # Output como PreferencesGroup > ExpanderRow > ActionRow > TextView
        # (substituiu TextView direto num Box, que pedia natural width
        # baseado no conteudo)
        # ------------------------------------------------------------
        log_expander = Adw.ExpanderRow()
        log_expander.set_title("Saida do scan")
        log_expander.set_subtitle("Output bruto (streaming em tempo real)")
        log_expander.set_expanded(True)

        self._output_view = Gtk.TextView()
        self._output_view.set_editable(False)
        self._output_view.set_cursor_visible(False)
        self._output_view.set_monospace(True)
        self._output_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._output_view.set_top_margin(8)
        self._output_view.set_bottom_margin(8)
        self._output_view.set_left_margin(8)
        self._output_view.set_right_margin(8)
        self._output_buffer = self._output_view.get_buffer()

        # Tags pra coloring
        self._tag_warning = self._output_buffer.create_tag(
            "warning", foreground="#fbbf24", weight=Pango.Weight.BOLD,
        )
        self._tag_infected = self._output_buffer.create_tag(
            "infected", foreground="#f87171", weight=Pango.Weight.BOLD,
        )

        log_scrolled = Gtk.ScrolledWindow()
        log_scrolled.set_min_content_height(240)
        log_scrolled.set_max_content_height(380)
        log_scrolled.set_child(self._output_view)

        log_row = Adw.ActionRow()
        log_row.set_child(log_scrolled)
        log_row.set_activatable(False)
        log_expander.add_row(log_row)

        log_group = Adw.PreferencesGroup()
        log_group.set_margin_top(16)
        log_group.add(log_expander)

        # ------------------------------------------------------------
        # Summary card (escondido ate scan terminar)
        # ------------------------------------------------------------
        self._summary_group = Adw.PreferencesGroup()
        self._summary_group.set_margin_top(16)
        self._summary_group.set_title("Resumo")
        self._summary_group.set_visible(False)

        self._row_status = Adw.ActionRow(title="Status")
        self._row_status.add_css_class("property")
        self._lbl_status = Gtk.Label(label="—")
        self._lbl_status.add_css_class("monospace")
        self._row_status.add_suffix(self._lbl_status)
        self._summary_group.add(self._row_status)

        self._row_elapsed = Adw.ActionRow(title="Tempo decorrido")
        self._row_elapsed.add_css_class("property")
        self._lbl_elapsed = Gtk.Label(label="—")
        self._lbl_elapsed.add_css_class("monospace")
        self._row_elapsed.add_suffix(self._lbl_elapsed)
        self._summary_group.add(self._row_elapsed)

        # ------------------------------------------------------------
        # Layout (pattern identico ao Antivirus scan tab)
        # ------------------------------------------------------------
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_top(24)
        inner.set_margin_bottom(28)
        inner.set_margin_start(28)
        inner.set_margin_end(28)
        inner.append(header_lbl)
        inner.append(header_desc)
        inner.append(action_box)
        inner.append(self._status_label)
        inner.append(self._kpis_group)
        inner.append(log_group)
        inner.append(self._summary_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(inner))

        # Banner fica fora do clamp para usar largura total
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.append(self._banner)
        outer.append(scrolled)
        self.set_child(outer)

        self.connect("destroy", self._on_destroy)
        self.refresh()

    def _on_destroy(self, *_a) -> None:
        self._destroyed = True

    # ============================================================
    # Refresh estado de instalacao
    # ============================================================

    def refresh(self) -> None:
        installed = self._installed_checker()
        if not installed:
            self._banner.set_title(
                f"{self._scanner_label} nao instalado. "
                f"Instale via Vigia Tool Installer "
                f"(pacote {self._install_pkg})."
            )
            self._banner.set_revealed(True)
            self._scan_btn.set_sensitive(False)
        else:
            self._banner.set_revealed(False)
            self._scan_btn.set_sensitive(True)

    # ============================================================
    # Scan flow
    # ============================================================

    def _on_scan_clicked(self, _btn) -> None:
        if self._running:
            return

        dlg = Adw.AlertDialog(
            heading=f"Iniciar scan {self._scanner_label}?",
            body=(
                f"O {self._scanner_label} vai rodar como root via pkexec.\n\n"
                f"Tempo aproximado:\n"
                f"  • chkrootkit: ~30s\n"
                f"  • rkhunter: 2-5min\n\n"
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
        self._scan_btn.set_sensitive(False)
        self._stop_btn.set_sensitive(True)
        self._summary_group.set_visible(False)
        self._output_buffer.set_text("")
        self._lbl_tests.set_label("0")
        self._lbl_warn.set_label("0")
        self._lbl_inf.set_label("0")
        self._set_label_color(self._lbl_warn, "")
        self._set_label_color(self._lbl_inf, "")
        self._status_label.set_label("Iniciando scan...")

        self._scan_starter(
            on_line=self._on_scan_line,
            on_done=self._on_scan_done,
            stop_flag=lambda: self._stop_requested,
        )

    def _on_stop_clicked(self, _btn) -> None:
        self._stop_requested = True
        self._status_label.set_label("Cancelando scan...")
        self._append_line("\n[Vigia] Cancelando scan...")

    # ============================================================
    # Streaming callbacks (do worker thread)
    # ============================================================

    def _on_scan_line(self, line: str) -> None:
        """Chamado do worker — agenda update na main thread."""
        GLib.idle_add(self._append_line, line)

    def _append_line(self, line: str) -> bool:
        if self._destroyed:
            return False
        # Append + classifica
        end_iter = self._output_buffer.get_end_iter()
        tag = None
        l = line.lower()
        if "infected" in l and "not infected" not in l:
            tag = self._tag_infected
        elif "warning" in l or "vulnerable" in l or "you have" in l:
            tag = self._tag_warning

        if tag is not None:
            self._output_buffer.insert_with_tags(end_iter, line + "\n", tag)
        else:
            self._output_buffer.insert(end_iter, line + "\n")

        # Auto-scroll
        mark = self._output_buffer.create_mark(None, self._output_buffer.get_end_iter(), False)
        self._output_view.scroll_to_mark(mark, 0, False, 0, 0)
        self._output_buffer.delete_mark(mark)

        # Atualiza KPIs em tempo real (counting linhas "Checking")
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
        self._scan_btn.set_sensitive(True)
        self._stop_btn.set_sensitive(False)

        # KPIs finais
        self._lbl_tests.set_label(str(result.tests_run))
        self._lbl_warn.set_label(str(result.warnings_count))
        self._lbl_inf.set_label(str(result.infected_count))

        if result.warnings_count > 0:
            self._set_label_color(self._lbl_warn, "warning")
        if result.infected_count > 0:
            self._set_label_color(self._lbl_inf, "error")

        # Status line + Summary
        self._summary_group.set_visible(True)
        for cls in ("success", "warning", "error", "dim-label"):
            self._lbl_status.remove_css_class(cls)
        if result.cancelled:
            self._lbl_status.set_label("cancelado")
            self._lbl_status.add_css_class("warning")
            self._status_label.set_label("Scan cancelado pelo usuario.")
        elif result.error:
            self._lbl_status.set_label("erro")
            self._lbl_status.add_css_class("error")
            self._status_label.set_label(f"Erro: {result.error[:120]}")
        elif result.infected_count > 0:
            self._lbl_status.set_label(f"{result.infected_count} infectado(s)")
            self._lbl_status.add_css_class("error")
            self._status_label.set_label(
                f"Scan completo: {result.infected_count} infectado(s) detectado(s)."
            )
        elif result.warnings_count > 0:
            self._lbl_status.set_label(f"{result.warnings_count} warning(s)")
            self._lbl_status.add_css_class("warning")
            self._status_label.set_label(
                f"Scan completo: {result.warnings_count} warning(s)."
            )
        else:
            self._lbl_status.set_label("limpo")
            self._lbl_status.add_css_class("success")
            self._status_label.set_label("Scan completo: nenhum sinal detectado.")
        self._lbl_elapsed.set_label(f"{result.elapsed_sec:.1f}s")

        # Dialog feedback
        if result.error and not result.cancelled:
            show_error(self, "Erro no scan", result.error)
        elif result.cancelled:
            show_info(self, "Scan cancelado", "Scan interrompido pelo usuario.")
        elif result.infected_count > 0:
            show_error(
                self,
                f"{self._scanner_label}: {result.infected_count} infectado(s)",
                "Revise a saida do scan e tome acoes apropriadas. "
                "Resultado salvo no Historico.",
            )
        elif result.warnings_count > 0:
            show_info(
                self,
                f"{self._scanner_label}: {result.warnings_count} warning(s)",
                "Sistema parece OK mas vale revisar warnings. "
                "Resultado salvo no Historico.",
            )
        else:
            show_info(
                self,
                f"{self._scanner_label}: limpo",
                "Nenhum sinal de rootkit detectado. "
                "Resultado salvo no Historico.",
            )

        return False

    @staticmethod
    def _set_label_color(label: Gtk.Label, level: str) -> None:
        for cls in ("success", "warning", "error"):
            label.remove_css_class(cls)
        if level:
            label.add_css_class(level)
