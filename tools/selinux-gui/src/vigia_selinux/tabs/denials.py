"""Tab Denials: lista de AVC denials recentes + audit2allow."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .. import backend
from ._helpers import make_clamp, show_error


# Mapeamento label -> argumento do ausearch
SINCE_OPTIONS = [
    ("Hoje", "today"),
    ("Esta semana", "this-week"),
    ("Recente (10 min)", "recent"),
    ("Este mes", "this-month"),
]


class DenialsTab(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        inner = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=8,
            margin_top=12, margin_bottom=12, margin_start=12, margin_end=12,
        )
        self.append(make_clamp(inner))

        # Barra superior: combo de periodo + botao carregar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        label = Gtk.Label(label="Periodo:")
        label.set_valign(Gtk.Align.CENTER)
        toolbar.append(label)

        self._since_dropdown = Gtk.DropDown.new_from_strings(
            [name for name, _ in SINCE_OPTIONS]
        )
        toolbar.append(self._since_dropdown)

        self._load_btn = Gtk.Button(label="Carregar denials")
        self._load_btn.add_css_class("suggested-action")
        self._load_btn.connect("clicked", lambda _b: self._load())
        toolbar.append(self._load_btn)

        toolbar.append(Gtk.Label(hexpand=True))  # spacer

        info = Gtk.Label()
        info.set_markup(
            '<small><i>Requer senha admin (pkexec) para ler audit.log.</i></small>'
        )
        info.set_valign(Gtk.Align.CENTER)
        toolbar.append(info)
        inner.append(toolbar)

        # Lista de denials
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self._list = Gtk.ListBox()
        self._list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list.add_css_class("boxed-list")
        scrolled.set_child(self._list)
        inner.append(scrolled)

        # Status (vazio inicialmente — usuario precisa clicar)
        self._render_empty("Clique 'Carregar denials' para buscar bloqueios recentes.")

    def _render_empty(self, message: str) -> None:
        while child := self._list.get_first_child():
            self._list.remove(child)
        row = Adw.ActionRow()
        row.set_title("Nenhum denial carregado")
        row.set_subtitle(message)
        self._list.append(row)

    def _load(self) -> None:
        idx = self._since_dropdown.get_selected()
        if idx >= len(SINCE_OPTIONS):
            idx = 0
        since = SINCE_OPTIONS[idx][1]

        self._load_btn.set_sensitive(False)
        self._load_btn.set_label("Carregando...")

        try:
            denials = backend.get_recent_denials(since=since)
        except Exception as e:
            self._render_empty(f"Erro: {e}")
            show_error(self, "Falha ao carregar denials", str(e))
            self._load_btn.set_sensitive(True)
            self._load_btn.set_label("Carregar denials")
            return

        self._render_denials(denials)
        self._load_btn.set_sensitive(True)
        self._load_btn.set_label("Carregar denials")

    def _render_denials(self, denials: list) -> None:
        while child := self._list.get_first_child():
            self._list.remove(child)
        if not denials:
            self._render_empty("Nenhum denial encontrado no periodo. SELinux esta tranquilo!")
            return
        # Mais recente primeiro
        for d in reversed(denials):
            row = self._build_denial_row(d)
            self._list.append(row)

    def _build_denial_row(self, d: backend.Denial) -> Adw.ExpanderRow:
        permissive_tag = "(permissive — apenas log)" if d.permissive else "(BLOQUEADO)"
        row = Adw.ExpanderRow()
        row.set_title(f"{d.comm} (pid {d.pid}) — {d.op} em '{d.name}' {permissive_tag}")
        row.set_subtitle(
            f"scontext: {d.scontext.split(':')[2] if d.scontext.count(':') >= 2 else d.scontext} → "
            f"tcontext: {d.tcontext.split(':')[2] if d.tcontext.count(':') >= 2 else d.tcontext} "
            f"({d.tclass})"
        )

        # Sub-row: raw + audit2allow button
        raw_row = Adw.ActionRow()
        raw_row.set_title("Linha raw do audit")
        raw_label = Gtk.Label()
        raw_label.set_label(d.raw)
        raw_label.set_wrap(True)
        raw_label.set_xalign(0)
        raw_label.add_css_class("dim-label")
        raw_label.add_css_class("caption")
        raw_label.set_selectable(True)
        raw_row.add_suffix(raw_label)
        row.add_row(raw_row)

        a2a_row = Adw.ActionRow()
        a2a_row.set_title("Sugerir fix via audit2allow")
        a2a_btn = Gtk.Button(label="Gerar")
        a2a_btn.set_valign(Gtk.Align.CENTER)
        a2a_btn.add_css_class("pill")
        a2a_btn.connect("clicked", lambda _b, d=d: self._show_audit2allow(d))
        a2a_row.add_suffix(a2a_btn)
        row.add_row(a2a_row)

        return row

    def _show_audit2allow(self, denial: backend.Denial) -> None:
        suggestion = backend.audit2allow_suggest(denial.raw)
        dlg = Adw.AlertDialog(
            heading=f"Policy sugerida para denial de '{denial.comm}'",
            body=f"audit2allow propos:\n\n{suggestion}\n\n"
            "Para aplicar como modulo custom: salve em arquivo.te, compile com\n"
            "  checkmodule -M -m -o arquivo.mod arquivo.te\n"
            "  semodule_package -o arquivo.pp -m arquivo.mod\n"
            "  semodule -i arquivo.pp",
        )
        dlg.add_response("ok", "Fechar")
        dlg.present(self.get_root())
