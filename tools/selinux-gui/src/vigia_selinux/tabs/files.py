"""Tab Files: restorecon para um path."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .. import backend
from ._helpers import make_clamp, show_error


class FilesTab(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        inner = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=12,
            margin_top=12, margin_bottom=12, margin_start=12, margin_end=12,
        )
        self.append(make_clamp(inner))

        # Cabecalho explicativo
        intro = Adw.PreferencesGroup()
        intro.set_title("Restaurar contextos SELinux (restorecon)")
        intro.set_description(
            "Quando voce move/cria arquivos em diretorios protegidos pelo SELinux, "
            "as labels podem ficar erradas e o app que usa esses arquivos falha. "
            "Esta ferramenta restaura as labels conforme as regras de file context."
        )
        inner.append(intro)

        # Input + botoes
        form_group = Adw.PreferencesGroup()
        form_group.set_title("Caminho a restaurar")

        self._path_row = Adw.EntryRow()
        self._path_row.set_title("Path (ex: /var/www, /srv, /home/andre/site)")
        self._path_row.set_text("")
        form_group.add(self._path_row)

        self._recursive_row = Adw.SwitchRow()
        self._recursive_row.set_title("Recursivo (-R)")
        self._recursive_row.set_subtitle("Aplica em todos os arquivos dentro do diretorio")
        self._recursive_row.set_active(True)
        form_group.add(self._recursive_row)

        self._verbose_row = Adw.SwitchRow()
        self._verbose_row.set_title("Verbose (-v)")
        self._verbose_row.set_subtitle("Lista cada arquivo que tiver label alterada")
        self._verbose_row.set_active(True)
        form_group.add(self._verbose_row)

        inner.append(form_group)

        # Botoes
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.END)
        self._restore_btn = Gtk.Button(label="Restaurar contextos")
        self._restore_btn.add_css_class("suggested-action")
        self._restore_btn.connect("clicked", lambda _b: self._do_restore())
        btn_box.append(self._restore_btn)
        inner.append(btn_box)

        # Output area
        out_group = Adw.PreferencesGroup()
        out_group.set_title("Saida do comando")
        out_scroll = Gtk.ScrolledWindow()
        out_scroll.set_vexpand(True)
        out_scroll.set_min_content_height(180)
        out_scroll.add_css_class("card")
        self._output_view = Gtk.TextView()
        self._output_view.set_editable(False)
        self._output_view.set_monospace(True)
        self._output_view.set_top_margin(8)
        self._output_view.set_bottom_margin(8)
        self._output_view.set_left_margin(8)
        self._output_view.set_right_margin(8)
        out_scroll.set_child(self._output_view)
        out_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        out_box.append(out_scroll)
        out_group.add(out_box)
        inner.append(out_group)

    def _do_restore(self) -> None:
        path = self._path_row.get_text().strip()
        if not path:
            show_error(self, "Path vazio", "Digite um path para restaurar.")
            return
        recursive = self._recursive_row.get_active()
        verbose = self._verbose_row.get_active()

        self._restore_btn.set_sensitive(False)
        self._restore_btn.set_label("Executando...")
        try:
            output = backend.restorecon(path, recursive=recursive, verbose=verbose)
            self._output_view.get_buffer().set_text(output)
        except Exception as e:
            show_error(self, "restorecon falhou", str(e))
            self._output_view.get_buffer().set_text(f"ERRO: {e}")
        finally:
            self._restore_btn.set_sensitive(True)
            self._restore_btn.set_label("Restaurar contextos")
