"""Tab Extrair: extrai arquivos embarcados de um binario."""

from __future__ import annotations

import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from ._helpers import make_clamp, make_file_picker_row, show_error, show_info


class ExtractTab(Adw.Bin):
    """Extrai arquivos detectados em um binario para outdir."""

    def __init__(self) -> None:
        super().__init__()
        self._running = False

        header_lbl = Gtk.Label(label="Extracao")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(4)

        header_desc = Gtk.Label(
            label=(
                "Extrai todos os arquivos detectados em um binario. Equivalente "
                "ao comando <tt>binwalk -e --directory=&lt;out&gt; &lt;arquivo&gt;</tt>.\n\n"
                "<b>Cuidado</b>: extracao pode gerar muitos arquivos. Use diretorio "
                "dedicado e revise antes de mover/abrir."
            )
        )
        header_desc.set_use_markup(True)
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(16)

        # Inputs
        input_group = Adw.PreferencesGroup()
        input_group.set_title("Parametros")

        self._target_entry = Gtk.Entry()
        self._target_entry.set_placeholder_text("/caminho/para/firmware.bin")
        self._target_entry.set_hexpand(True)
        input_group.add(make_file_picker_row("Arquivo de entrada", self._target_entry))

        self._outdir_entry = Gtk.Entry()
        default_outdir = str(Path.home() / "vigia-firmware-extracted")
        self._outdir_entry.set_text(default_outdir)
        self._outdir_entry.set_placeholder_text("Diretorio de output")
        self._outdir_entry.set_hexpand(True)
        input_group.add(make_file_picker_row("Diretorio de saida", self._outdir_entry, folder_only=True))

        # Run
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_margin_top(12)
        action_box.set_margin_bottom(12)
        self._run_btn = Gtk.Button(label="Extrair")
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

        # Result info
        self._result_group = Adw.PreferencesGroup()
        self._result_group.set_title("Resultado")
        self._result_row = Adw.ActionRow(title="Nenhuma extracao ainda")
        self._result_row.add_css_class("dim-label")
        self._result_group.add(self._result_row)

        # Layout
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(20)
        outer.set_margin_bottom(20)
        outer.set_margin_start(20)
        outer.set_margin_end(20)
        outer.append(header_lbl)
        outer.append(header_desc)
        outer.append(input_group)
        outer.append(action_box)
        outer.append(self._status_label)
        outer.append(self._result_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

    def _start(self) -> None:
        if self._running:
            return

        path = self._target_entry.get_text().strip()
        outdir = self._outdir_entry.get_text().strip()
        if not path:
            show_error(self, "Sem arquivo", "Informe o arquivo de entrada.")
            return
        if not outdir:
            show_error(self, "Sem outdir", "Informe o diretorio de saida.")
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
        self._outdir_entry.set_sensitive(False)
        self._spinner.start()
        self._status_label.set_label("Extraindo... pode levar 30s-5min em firmware grande.")

        threading.Thread(target=self._worker, args=(path, outdir), daemon=True).start()

    def _worker(self, path: str, outdir: str) -> None:
        result = backend.extract_blocking(path, outdir)
        GLib.idle_add(self._on_done, result)

    def _on_done(self, result: backend.ExtractResult) -> bool:
        self._running = False
        self._run_btn.set_sensitive(True)
        self._target_entry.set_sensitive(True)
        self._outdir_entry.set_sensitive(True)
        self._spinner.stop()

        if result.error:
            self._status_label.set_label(f"Erro: {result.error}")
            return False

        self._status_label.set_label(
            f"Concluido em {result.elapsed_sec}s. "
            f"{result.file_count} arquivo{'s' if result.file_count != 1 else ''} extraido{'s' if result.file_count != 1 else ''}."
        )

        # Update result row
        self._result_row.set_title("Extracao concluida")
        self._result_row.set_subtitle(
            f"{result.file_count} arquivo{'s' if result.file_count != 1 else ''} em "
            f"{result.outdir}/_<basename>.extracted/"
        )
        for cls in ("dim-label",):
            self._result_row.remove_css_class(cls)

        show_info(
            self,
            "Extracao concluida",
            f"{result.file_count} arquivo(s) em {result.outdir}.",
        )
        return False
