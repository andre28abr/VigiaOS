"""Tab Entropia: visualiza pontos de mudanca de entropia."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from ._helpers import make_clamp, make_file_picker_row, show_error


class EntropyTab(Adw.Bin):
    """Mostra edges de mudanca de entropia."""

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._last_result: backend.EntropyResult | None = None

        header_lbl = Gtk.Label(label="Analise de entropia")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(8)

        header_desc = Gtk.Label(
            label=(
                "Mostra <b>edges</b> (pontos de mudanca brusca) de entropia ao "
                "longo do arquivo. Entropia alta (~0.95+) indica dados "
                "compactados/criptografados; baixa (~0.3-) indica padroes "
                "estruturados (codigo, texto, headers).\n\n"
                "Util para encontrar regioes interessantes em firmware sem "
                "saber a estrutura previamente."
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
        input_group.set_title("Arquivo")

        self._target_entry = Gtk.Entry()
        self._target_entry.set_placeholder_text("/caminho/para/firmware.bin")
        self._target_entry.set_hexpand(True)
        input_group.add(make_file_picker_row("Arquivo", self._target_entry))

        # Run
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_margin_top(12)
        action_box.set_margin_bottom(12)
        self._run_btn = Gtk.Button(label="Calcular entropia")
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
        self._results_group.set_title("Edges detectados")
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
            show_error(self, "Sem arquivo", "Informe o arquivo a analisar.")
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
        self._status_label.set_label("Calculando entropia... pode levar 30s-2min.")

        threading.Thread(target=self._worker, args=(path,), daemon=True).start()

    def _worker(self, path: str) -> None:
        result = backend.entropy_blocking(path)
        GLib.idle_add(self._on_done, result)

    def _on_done(self, result: backend.EntropyResult) -> bool:
        self._running = False
        self._run_btn.set_sensitive(True)
        self._target_entry.set_sensitive(True)
        self._spinner.stop()

        if result.error:
            self._status_label.set_label(f"Erro: {result.error}")
            return False

        n = len(result.points)
        self._status_label.set_label(
            f"Concluido em {result.elapsed_sec}s — "
            f"{n} edge{'s' if n != 1 else ''} detectado{'s' if n != 1 else ''}. "
            "Curva visual chega em v0.2."
        )

        self._last_result = result
        self._render_results()
        return False

    def _render_results(self) -> None:
        for r in self._results_rows:
            self._results_group.remove(r)
        self._results_rows = []

        if self._last_result is None or not self._last_result.points:
            row = Adw.ActionRow(title="Sem edges ainda")
            row.set_subtitle(
                "Execute analise para popular esta lista."
                if self._last_result is None
                else "Entropia uniforme — provavelmente um tipo unico de conteudo."
            )
            row.add_css_class("dim-label")
            self._results_group.add(row)
            self._results_rows.append(row)
            return

        for pt in self._last_result.points:
            row = Adw.ActionRow(title=f"offset {pt.offset:>12,d}")
            ent_str = f"entropia {pt.entropy:.3f}"
            if pt.entropy >= 0.95:
                ent_str += " (compactado/encryptado)"
                cls = "warning"
            elif pt.entropy >= 0.6:
                ent_str += " (dados densos)"
                cls = "dim-label"
            elif pt.entropy >= 0.3:
                ent_str += " (dados estruturados)"
                cls = "success"
            else:
                ent_str += " (padrao repetitivo)"
                cls = "success"
            row.set_subtitle(ent_str)
            row.add_css_class("property")

            badge = Gtk.Label(label=f"{pt.entropy:.2f}")
            badge.add_css_class("monospace")
            badge.add_css_class("caption-heading")
            badge.add_css_class(cls)
            badge.set_valign(Gtk.Align.CENTER)
            row.add_suffix(badge)

            self._results_group.add(row)
            self._results_rows.append(row)
