"""Tab Verificar: compara hash conhecido vs computado."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from ._helpers import make_clamp, make_file_picker_row, show_error


class VerifyTab(Adw.Bin):
    """Compara hash esperado contra computado."""

    def __init__(self) -> None:
        super().__init__()
        self._running = False

        # Header
        header_lbl = Gtk.Label(label="Verificar hash")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(8)

        header_desc = Gtk.Label(
            label=(
                "Compara um hash <i>esperado</i> (que voce recebeu de uma fonte "
                "confiavel) contra o hash <i>computado</i> do arquivo local. "
                "Bate: arquivo intacto. Nao bate: arquivo corrompido ou adulterado."
            )
        )
        header_desc.set_use_markup(True)
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(24)

        # Inputs
        input_group = Adw.PreferencesGroup()
        input_group.set_title("Parametros")

        self._target_entry = Gtk.Entry()
        self._target_entry.set_placeholder_text("/caminho/para/arquivo")
        self._target_entry.set_hexpand(True)
        input_group.add(make_file_picker_row("Arquivo", self._target_entry))

        self._expected_entry = Gtk.Entry()
        self._expected_entry.set_placeholder_text("hash hexadecimal esperado")
        self._expected_entry.set_hexpand(True)
        exp_row = Adw.ActionRow(title="Hash esperado")
        exp_row.set_subtitle(
            "Aceita formato 'hash  filename' (output do sha256sum). "
            "Apenas a parte hexadecimal e' usada."
        )
        exp_row.set_subtitle_lines(2)
        exp_row.add_suffix(self._expected_entry)
        input_group.add(exp_row)

        self._algo_combo = Gtk.DropDown.new_from_strings(backend.list_algorithms())
        self._algo_combo.set_selected(0)
        algo_row = Adw.ActionRow(title="Algoritmo")
        algo_row.add_suffix(self._algo_combo)
        input_group.add(algo_row)

        # Run
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_margin_top(12)
        action_box.set_margin_bottom(12)
        self._run_btn = Gtk.Button(label="Verificar")
        self._run_btn.add_css_class("suggested-action")
        self._run_btn.connect("clicked", lambda _b: self._start())
        action_box.append(self._run_btn)

        self._spinner = Gtk.Spinner()
        action_box.append(self._spinner)

        # Result hero
        self._verdict_label = Gtk.Label(label="(aguardando verificacao)")
        self._verdict_label.add_css_class("title-2")
        self._verdict_label.add_css_class("dim-label")
        self._verdict_label.set_halign(Gtk.Align.CENTER)
        self._verdict_label.set_margin_top(12)
        self._verdict_label.set_margin_bottom(4)

        self._verdict_sub = Gtk.Label(label="")
        self._verdict_sub.add_css_class("dim-label")
        self._verdict_sub.set_halign(Gtk.Align.CENTER)
        self._verdict_sub.set_wrap(True)
        self._verdict_sub.set_max_width_chars(60)
        self._verdict_sub.set_margin_bottom(12)

        # Details
        self._details_group = Adw.PreferencesGroup()
        self._details_group.set_margin_top(24)
        self._details_group.set_title("Detalhes")

        self._exp_row = Adw.ActionRow(title="Esperado")
        self._exp_row.add_css_class("property")
        self._exp_lbl = Gtk.Label(label="—")
        self._exp_lbl.add_css_class("monospace")
        self._exp_lbl.add_css_class("caption")
        self._exp_lbl.set_wrap(True)
        self._exp_lbl.set_wrap_mode(Gtk.WrapMode.CHAR)
        self._exp_row.add_suffix(self._exp_lbl)
        self._details_group.add(self._exp_row)

        self._got_row = Adw.ActionRow(title="Computado")
        self._got_row.add_css_class("property")
        self._got_lbl = Gtk.Label(label="—")
        self._got_lbl.add_css_class("monospace")
        self._got_lbl.add_css_class("caption")
        self._got_lbl.set_wrap(True)
        self._got_lbl.set_wrap_mode(Gtk.WrapMode.CHAR)
        self._got_row.add_suffix(self._got_lbl)
        self._details_group.add(self._got_row)

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
        outer.append(self._verdict_label)
        outer.append(self._verdict_sub)
        outer.append(self._details_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

    def _start(self) -> None:
        if self._running:
            return
        path = self._target_entry.get_text().strip()
        expected = self._expected_entry.get_text().strip()
        if not path:
            show_error(self, "Sem arquivo", "Informe o caminho.")
            return
        if not expected:
            show_error(self, "Sem hash", "Informe o hash esperado.")
            return

        algo = backend.list_algorithms()[self._algo_combo.get_selected()]

        self._running = True
        self._run_btn.set_sensitive(False)
        self._target_entry.set_sensitive(False)
        self._expected_entry.set_sensitive(False)
        self._algo_combo.set_sensitive(False)
        self._spinner.start()

        for cls in ("success", "error", "warning", "dim-label"):
            self._verdict_label.remove_css_class(cls)
        self._verdict_label.set_label("Calculando...")
        self._verdict_label.add_css_class("dim-label")
        self._verdict_sub.set_label("")

        threading.Thread(target=self._worker, args=(path, expected, algo), daemon=True).start()

    def _worker(self, path: str, expected: str, algo: str) -> None:
        matches, computed, err = backend.verify_blocking(path, expected, algo)
        GLib.idle_add(self._on_done, matches, computed, err, expected, algo)

    def _on_done(
        self, matches: bool, computed: str, err: str,
        expected_raw: str, algo: str,
    ) -> bool:
        self._running = False
        self._run_btn.set_sensitive(True)
        self._target_entry.set_sensitive(True)
        self._expected_entry.set_sensitive(True)
        self._algo_combo.set_sensitive(True)
        self._spinner.stop()

        for cls in ("success", "error", "warning", "dim-label"):
            self._verdict_label.remove_css_class(cls)

        if err:
            self._verdict_label.set_label("Erro")
            self._verdict_label.add_css_class("warning")
            self._verdict_sub.set_label(err)
            self._exp_lbl.set_label("—")
            self._got_lbl.set_label("—")
            return False

        # Normalize expected (caller pode ter passado "hash filename")
        expected_clean = expected_raw.split()[0].strip().lower() if expected_raw else ""

        self._exp_lbl.set_label(expected_clean or "—")
        self._got_lbl.set_label(computed)

        if matches:
            self._verdict_label.set_label("✓ Hashes batem")
            self._verdict_label.add_css_class("success")
            self._verdict_sub.set_label(
                f"Arquivo intacto. {algo.upper()} bate com o hash esperado."
            )
        else:
            self._verdict_label.set_label("✗ Hashes nao batem")
            self._verdict_label.add_css_class("error")
            self._verdict_sub.set_label(
                "Arquivo CORROMPIDO ou ADULTERADO. Nao confie no conteudo "
                "ate investigar a fonte do hash esperado."
            )

        return False
