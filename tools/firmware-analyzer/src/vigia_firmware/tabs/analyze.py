"""Tab Analisar: detecta signatures em arquivo."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from ._helpers import make_clamp, make_file_picker_row, show_error


class AnalyzeTab(Adw.Bin):
    """Detecta signatures em arquivo binario."""

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._last_result: backend.AnalyzeResult | None = None

        # Header
        header_lbl = Gtk.Label(label="Analise de signatures")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(8)

        header_desc = Gtk.Label(
            label=(
                "Detecta arquivos embarcados (imagens, archives, filesystems, "
                "kernels, etc.) num blob binario via magic numbers. Equivalente "
                "ao comando <tt>binwalk &lt;arquivo&gt;</tt>."
            )
        )
        header_desc.set_use_markup(True)
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(24)

        # Input
        input_group = Adw.PreferencesGroup()
        input_group.set_title("Arquivo de entrada")

        self._target_entry = Gtk.Entry()
        self._target_entry.set_placeholder_text("/caminho/para/firmware.bin")
        self._target_entry.set_hexpand(True)
        input_group.add(make_file_picker_row("Arquivo", self._target_entry))

        # Run
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_margin_top(12)
        action_box.set_margin_bottom(12)
        self._run_btn = Gtk.Button(label="Analisar")
        self._run_btn.add_css_class("suggested-action")
        self._run_btn.connect("clicked", lambda _b: self._start())
        action_box.append(self._run_btn)

        self._spinner = Gtk.Spinner()
        action_box.append(self._spinner)

        self._status_label = Gtk.Label(label="")
        self._status_label.add_css_class("dim-label")
        self._status_label.set_halign(Gtk.Align.START)
        self._status_label.set_wrap(True)
        self._status_label.set_xalign(0)

        # Results
        self._results_group = Adw.PreferencesGroup()
        self._results_group.set_margin_top(24)
        self._results_group.set_title("Signatures detectadas")
        self._results_rows: list = []
        self._render_results()

        # Layout
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(24)
        outer.set_margin_bottom(32)
        outer.set_margin_start(28)
        outer.set_margin_end(28)
        outer.append(header_lbl)
        outer.append(header_desc)
        outer.append(input_group)
        outer.append(action_box)
        outer.append(self._status_label)
        outer.append(self._results_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

    def _start(self) -> None:
        if self._running:
            return

        path = self._target_entry.get_text().strip()
        if not path:
            show_error(self, "Sem arquivo", "Informe o caminho do arquivo a analisar.")
            return
        if not backend.binwalk_installed():
            show_error(
                self,
                "binwalk nao instalado",
                "Instale com: rpm-ostree install binwalk && reboot",
            )
            return

        self._running = True
        self._run_btn.set_sensitive(False)
        self._target_entry.set_sensitive(False)
        self._spinner.start()
        self._status_label.set_label("Analisando... pode levar 10-60s em firmware grande.")

        threading.Thread(target=self._worker, args=(path,), daemon=True).start()

    def _worker(self, path: str) -> None:
        result = backend.analyze_blocking(path)
        GLib.idle_add(self._on_done, result)

    def _on_done(self, result: backend.AnalyzeResult) -> bool:
        self._running = False
        self._run_btn.set_sensitive(True)
        self._target_entry.set_sensitive(True)
        self._spinner.stop()

        if result.error:
            self._status_label.set_label(f"Erro: {result.error}")
            return False

        n = len(result.signatures)
        self._status_label.set_label(
            f"Concluido em {result.elapsed_sec}s — "
            f"{n} signature{'s' if n != 1 else ''} detectada{'s' if n != 1 else ''}."
        )

        self._last_result = result
        self._render_results()
        return False

    def _render_results(self) -> None:
        for r in self._results_rows:
            self._results_group.remove(r)
        self._results_rows = []

        if self._last_result is None or not self._last_result.signatures:
            row = Adw.ActionRow(title="Nenhuma signature ainda")
            row.set_subtitle(
                "Execute uma analise para popular esta lista."
                if self._last_result is None
                else "Arquivo nao contem signatures conhecidas (ou e' uniforme)."
            )
            row.add_css_class("dim-label")
            self._results_group.add(row)
            self._results_rows.append(row)
            return

        for sig in self._last_result.signatures:
            row = Adw.ActionRow(title=sig.description)
            row.set_subtitle(f"offset: {sig.offset} ({sig.offset_hex})")
            row.set_subtitle_lines(2)
            row.add_css_class("property")

            off_lbl = Gtk.Label(label=sig.offset_hex)
            off_lbl.add_css_class("monospace")
            off_lbl.add_css_class("caption")
            off_lbl.set_valign(Gtk.Align.CENTER)
            row.add_suffix(off_lbl)

            self._results_group.add(row)
            self._results_rows.append(row)
