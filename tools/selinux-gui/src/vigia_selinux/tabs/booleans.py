"""Tab Booleans: lista pesquisavel de SELinux booleans com descricoes pt-BR."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .. import backend
from ._helpers import make_clamp, show_error


class BooleansTab(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        # Conteudo interno (sera wrappado em Adw.Clamp para limitar largura)
        inner = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=8,
            margin_top=12, margin_bottom=12, margin_start=12, margin_end=12,
        )
        self.append(make_clamp(inner))

        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text(
            "Filtrar por nome ou descricao (ex: apache, write, anonimo, ssh)"
        )
        self._search_entry.connect("search-changed", self._on_search_changed)
        inner.append(self._search_entry)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._list = Gtk.ListBox()
        self._list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list.add_css_class("boxed-list")
        self._list.set_filter_func(self._filter)
        scrolled.set_child(self._list)
        inner.append(scrolled)

        btn = Gtk.Button(label="Recarregar lista")
        btn.set_halign(Gtk.Align.END)
        btn.connect("clicked", lambda _b: self._refresh())
        inner.append(btn)

        self._row_search_text: dict[Adw.ActionRow, str] = {}
        self._refresh()

    def _refresh(self) -> None:
        while child := self._list.get_first_child():
            self._list.remove(child)
        self._row_search_text.clear()

        booleans = backend.list_booleans()
        if not booleans:
            empty = Adw.ActionRow()
            empty.set_title("Nenhum boolean encontrado")
            empty.set_subtitle("SELinux pode nao estar instalado ou sem policy carregada.")
            self._list.append(empty)
            return

        for b in sorted(booleans, key=lambda x: x.name):
            row = Adw.ActionRow()
            row.set_title(b.name)
            row.set_subtitle(b.display_description)

            switch = Gtk.Switch()
            switch.set_valign(Gtk.Align.CENTER)
            switch.set_active(b.value)
            switch.connect(
                "state-set",
                lambda sw, val, name=b.name: self._on_toggle(sw, val, name),
            )
            row.add_suffix(switch)
            row.set_activatable_widget(switch)

            self._row_search_text[row] = (
                b.name.lower() + " " + b.display_description.lower()
            )
            self._list.append(row)

    def _filter(self, row: Gtk.ListBoxRow) -> bool:
        query = self._search_entry.get_text().lower().strip()
        if not query:
            return True
        haystack = self._row_search_text.get(row)
        if haystack is None:
            return True
        return query in haystack

    def _on_search_changed(self, _entry: Gtk.SearchEntry) -> None:
        self._list.invalidate_filter()

    def _on_toggle(self, switch: Gtk.Switch, value: bool, name: str) -> bool:
        try:
            backend.set_boolean(name, value, persistent=True)
            switch.set_state(value)
        except Exception as e:
            switch.set_state(not value)
            show_error(self, f"Falha ao mudar '{name}'", str(e))
        return True
