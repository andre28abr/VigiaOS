"""Widget de scan compartilhado entre chkrootkit e rkhunter tabs.

Estrutura:
- Header: nome do scanner + descricao
- Banner: status (nao instalado / pronto / rodando / concluido)
- Action row: botao Iniciar Scan / Parar Scan
- KPI cards (3): testes, warnings, infected
- Output (TextView read-only, monospace, streaming)
- Summary card (mostrado apos scan termina)
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
    """Widget generico de scan.

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

        # ===== Header =====
        header_lbl = Gtk.Label(label=scanner_label)
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(8)

        desc_lbl = Gtk.Label()
        desc_lbl.set_markup(description)
        desc_lbl.add_css_class("dim-label")
        desc_lbl.set_halign(Gtk.Align.START)
        desc_lbl.set_wrap(True)
        desc_lbl.set_xalign(0)
        desc_lbl.set_margin_bottom(20)
        # v0.1.2: max_width_chars FORCA o Label a calcular natural size
        # baseado em 60 chars (nao no texto inteiro). Sem isso, Label com
        # wrap=True ainda pedia natural size do texto TODO (~280 chars
        # = ~3000px), fazendo a janela do Hub esticar.
        desc_lbl.set_max_width_chars(60)
        desc_lbl.set_width_chars(40)  # min hint

        # ===== Banner =====
        self._banner = Adw.Banner()
        self._banner.set_revealed(False)

        # ===== Action =====
        self._action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._action_box.set_halign(Gtk.Align.CENTER)
        self._action_box.set_margin_bottom(20)

        self._scan_btn = Gtk.Button(label="Iniciar scan")
        self._scan_btn.add_css_class("suggested-action")
        self._scan_btn.connect("clicked", self._on_scan_clicked)
        self._action_box.append(self._scan_btn)

        self._stop_btn = Gtk.Button(label="Parar")
        self._stop_btn.add_css_class("destructive-action")
        self._stop_btn.set_visible(False)
        self._stop_btn.connect("clicked", self._on_stop_clicked)
        self._action_box.append(self._stop_btn)

        # ===== KPIs (3 cards) =====
        kpis_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        kpis_box.set_halign(Gtk.Align.CENTER)
        kpis_box.set_margin_bottom(20)

        self._kpi_tests = self._build_kpi("Testes", "—")
        kpis_box.append(self._kpi_tests["widget"])

        self._kpi_warn = self._build_kpi("Warnings", "—")
        kpis_box.append(self._kpi_warn["widget"])

        self._kpi_inf = self._build_kpi("Infectados", "—")
        kpis_box.append(self._kpi_inf["widget"])

        # ===== Output (TextView read-only, monospace) =====
        output_lbl = Gtk.Label(label="Saida")
        output_lbl.add_css_class("heading")
        output_lbl.set_halign(Gtk.Align.START)
        output_lbl.set_margin_bottom(4)

        self._output_buffer = Gtk.TextBuffer()
        self._output_view = Gtk.TextView(buffer=self._output_buffer)
        self._output_view.set_editable(False)
        self._output_view.set_cursor_visible(False)
        self._output_view.set_monospace(True)
        self._output_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._output_view.add_css_class("card")
        self._output_view.set_margin_top(0)

        output_scrolled = Gtk.ScrolledWindow()
        # v0.1.1: hscrollbar NEVER pra forcar wrap horizontal do TextView.
        # Era AUTOMATIC, mas linhas longas do chkrootkit (paths /usr/lib/...)
        # esticavam o widget pedindo natural size grande, fazendo a janela
        # do Hub expandir lateralmente.
        output_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        output_scrolled.set_min_content_height(280)
        output_scrolled.set_max_content_height(420)
        output_scrolled.set_child(self._output_view)
        output_scrolled.set_margin_bottom(16)
        # Garante que nao pede largura excessiva
        output_scrolled.set_hexpand(False)

        # Tag pra coloring linhas relevantes
        self._tag_warning = self._output_buffer.create_tag(
            "warning", foreground="#fbbf24", weight=Pango.Weight.BOLD,
        )
        self._tag_infected = self._output_buffer.create_tag(
            "infected", foreground="#f87171", weight=Pango.Weight.BOLD,
        )

        # ===== Summary card (escondido ate scan terminar) =====
        self._summary_group = Adw.PreferencesGroup()
        self._summary_group.set_visible(False)
        self._summary_group.set_title("Resumo")

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

        # ===== Layout =====
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_top(24)
        inner.set_margin_bottom(32)
        inner.set_margin_start(28)
        inner.set_margin_end(28)
        inner.append(header_lbl)
        inner.append(desc_lbl)
        inner.append(self._action_box)
        inner.append(kpis_box)
        inner.append(output_lbl)
        inner.append(output_scrolled)
        inner.append(self._summary_group)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        # v0.1.1: hexpand True faz o Box preencher a area disponivel ao
        # inves de pedir mais largura — previne janela do Hub esticar.
        outer.set_hexpand(True)
        outer.append(self._banner)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_child(make_clamp(inner))
        outer.append(scrolled)
        self.set_child(outer)

        self.connect("destroy", self._on_destroy)
        self.refresh()

    def _on_destroy(self, *_a) -> None:
        self._destroyed = True

    def _build_kpi(self, label: str, default: str) -> dict:
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        card.add_css_class("card")
        card.set_size_request(150, 80)

        val_lbl = Gtk.Label(label=default)
        val_lbl.add_css_class("title-1")
        val_lbl.set_halign(Gtk.Align.CENTER)
        val_lbl.set_margin_top(10)
        card.append(val_lbl)

        lbl = Gtk.Label(label=label)
        lbl.add_css_class("caption")
        lbl.add_css_class("dim-label")
        lbl.set_halign(Gtk.Align.CENTER)
        lbl.set_margin_bottom(10)
        card.append(lbl)

        return {"widget": card, "val": val_lbl}

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

        # Confirmacao com aviso de tempo
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
        self._scan_btn.set_visible(False)
        self._stop_btn.set_visible(True)
        self._summary_group.set_visible(False)
        self._output_buffer.set_text("")
        self._kpi_tests["val"].set_label("0")
        self._kpi_warn["val"].set_label("0")
        self._kpi_inf["val"].set_label("0")
        self._set_kpi_color(self._kpi_warn["val"], "")
        self._set_kpi_color(self._kpi_inf["val"], "")

        self._scan_starter(
            on_line=self._on_scan_line,
            on_done=self._on_scan_done,
            stop_flag=lambda: self._stop_requested,
        )

    def _on_stop_clicked(self, _btn) -> None:
        self._stop_requested = True
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
                current = int(self._kpi_tests["val"].get_label() or "0")
                self._kpi_tests["val"].set_label(str(current + 1))
            except (ValueError, TypeError):
                pass

        return False

    def _on_scan_done(self, result: backend.ScanResult) -> None:
        GLib.idle_add(self._on_scan_done_ui, result)

    def _on_scan_done_ui(self, result: backend.ScanResult) -> bool:
        if self._destroyed:
            return False
        self._running = False
        self._scan_btn.set_visible(True)
        self._stop_btn.set_visible(False)

        # KPIs finais
        self._kpi_tests["val"].set_label(str(result.tests_run))
        self._kpi_warn["val"].set_label(str(result.warnings_count))
        self._kpi_inf["val"].set_label(str(result.infected_count))

        if result.warnings_count > 0:
            self._set_kpi_color(self._kpi_warn["val"], "warning")
        if result.infected_count > 0:
            self._set_kpi_color(self._kpi_inf["val"], "error")

        # Summary
        self._summary_group.set_visible(True)
        for cls in ("success", "warning", "error", "dim-label"):
            self._lbl_status.remove_css_class(cls)
        if result.cancelled:
            self._lbl_status.set_label("cancelado")
            self._lbl_status.add_css_class("warning")
        elif result.error:
            self._lbl_status.set_label("erro")
            self._lbl_status.add_css_class("error")
        elif result.infected_count > 0:
            self._lbl_status.set_label(f"{result.infected_count} infectado(s)")
            self._lbl_status.add_css_class("error")
        elif result.warnings_count > 0:
            self._lbl_status.set_label(f"{result.warnings_count} warning(s)")
            self._lbl_status.add_css_class("warning")
        else:
            self._lbl_status.set_label("limpo")
            self._lbl_status.add_css_class("success")
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
    def _set_kpi_color(label: Gtk.Label, level: str) -> None:
        for cls in ("success", "warning", "error"):
            label.remove_css_class(cls)
        if level:
            label.add_css_class(level)
