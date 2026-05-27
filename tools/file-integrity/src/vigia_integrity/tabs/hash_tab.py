"""Tab Hash: calcula hash de arquivo."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import hash_backend as backend
from ._helpers import (
    copy_to_clipboard,
    make_clamp,
    make_file_picker_row,
    show_error,
    show_info,
)


class HashTab(Adw.Bin):
    """Calcula hash de um arquivo unico."""

    def __init__(self) -> None:
        super().__init__()
        self._running = False

        # Header
        header_lbl = Gtk.Label(label="Calcular hash")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(8)

        header_desc = Gtk.Label(
            label=(
                "Calcula o digest criptografico de um arquivo. Use para "
                "verificar integridade de downloads, gerar fingerprints de "
                "evidencias forenses ou comparar versoes."
            )
        )
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

        # Algorithm
        self._algo_combo = Gtk.DropDown.new_from_strings(backend.list_algorithms())
        self._algo_combo.set_selected(0)  # sha256
        algo_row = Adw.ActionRow(title="Algoritmo")
        algo_row.set_subtitle("SHA-256 e' o padrao moderno. MD5/SHA-1 so para compatibilidade.")
        algo_row.add_suffix(self._algo_combo)
        input_group.add(algo_row)

        # Run
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_margin_top(12)
        action_box.set_margin_bottom(12)
        self._run_btn = Gtk.Button(label="Calcular")
        self._run_btn.add_css_class("suggested-action")
        self._run_btn.connect("clicked", lambda _b: self._start())
        action_box.append(self._run_btn)

        self._spinner = Gtk.Spinner()
        action_box.append(self._spinner)

        # Result
        self._result_group = Adw.PreferencesGroup()
        self._result_group.set_margin_top(24)
        self._result_group.set_title("Resultado")

        self._result_view = Gtk.TextView()
        self._result_view.set_editable(False)
        self._result_view.set_monospace(True)
        self._result_view.set_wrap_mode(Gtk.WrapMode.CHAR)
        self._result_view.set_top_margin(8)
        self._result_view.set_bottom_margin(8)
        self._result_view.set_left_margin(8)
        self._result_view.set_right_margin(8)
        self._result_buf = self._result_view.get_buffer()
        self._result_buf.set_text("(nenhum hash calculado ainda)")

        result_scrolled = Gtk.ScrolledWindow()
        result_scrolled.set_min_content_height(80)
        result_scrolled.set_max_content_height(140)
        result_scrolled.add_css_class("card")
        result_scrolled.set_child(self._result_view)

        result_row = Adw.PreferencesRow()
        result_row.set_child(result_scrolled)
        result_row.set_activatable(False)
        self._result_group.add(result_row)

        # Copy action — botao FORA do card pra ter espaco proprio
        copy_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        copy_box.set_halign(Gtk.Align.END)
        copy_box.set_margin_top(16)
        self._copy_btn = Gtk.Button(label="Copiar")
        self._copy_btn.set_sensitive(False)
        self._copy_btn.connect("clicked", lambda _b: self._do_copy())
        copy_box.append(self._copy_btn)

        self._status_label = Gtk.Label(label="")
        self._status_label.add_css_class("dim-label")
        self._status_label.set_halign(Gtk.Align.START)
        self._status_label.set_wrap(True)
        self._status_label.set_xalign(0)

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
        outer.append(self._result_group)
        outer.append(copy_box)

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
            show_error(self, "Sem arquivo", "Informe o caminho do arquivo.")
            return

        algo = backend.list_algorithms()[self._algo_combo.get_selected()]

        self._running = True
        self._run_btn.set_sensitive(False)
        self._target_entry.set_sensitive(False)
        self._algo_combo.set_sensitive(False)
        self._copy_btn.set_sensitive(False)
        self._spinner.start()
        self._status_label.set_label("Calculando...")

        threading.Thread(target=self._worker, args=(path, algo), daemon=True).start()

    def _worker(self, path: str, algo: str) -> None:
        h, err = backend.hash_blocking(path, algo)
        GLib.idle_add(self._on_done, h, err, algo)

    def _on_done(self, h: str, err: str, algo: str) -> bool:
        self._running = False
        self._run_btn.set_sensitive(True)
        self._target_entry.set_sensitive(True)
        self._algo_combo.set_sensitive(True)
        self._spinner.stop()

        if err:
            self._status_label.set_label(f"Erro: {err}")
            self._result_buf.set_text("(erro)")
            self._copy_btn.set_sensitive(False)
            return False

        self._status_label.set_label(f"Hash {algo.upper()} calculado.")
        self._result_buf.set_text(h)
        self._copy_btn.set_sensitive(True)
        return False

    def _do_copy(self) -> None:
        start, end = self._result_buf.get_bounds()
        text = self._result_buf.get_text(start, end, False)
        copy_to_clipboard(self, text)
        show_info(self, "Copiado", "Hash copiado para a area de transferencia.")
