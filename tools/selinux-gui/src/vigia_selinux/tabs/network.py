"""Tab Network: lista de port mappings SELinux (read-only v0.1)."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .. import backend


class NetworkTab(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL, spacing=8,
            margin_top=12, margin_bottom=12, margin_start=12, margin_end=12,
        )

        intro = Gtk.Label()
        intro.set_markup(
            "<b>Port mappings SELinux</b> — quais portas pertencem a qual contexto. "
            "Ex: se voce roda Apache em porta 8000, precisa adicionar 8000 a "
            "<tt>http_port_t</tt> via <tt>semanage port -a</tt> (escrita virá em v0.2)."
        )
        intro.set_wrap(True)
        intro.set_xalign(0)
        self.append(intro)

        # Search
        self._search = Gtk.SearchEntry()
        self._search.set_placeholder_text("Filtrar por contexto ou porta (ex: http, 80, ssh)")
        self._search.connect("search-changed", lambda _e: self._list.invalidate_filter())
        self.append(self._search)

        # Lista
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self._list = Gtk.ListBox()
        self._list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list.add_css_class("boxed-list")
        self._list.set_filter_func(self._filter)
        scrolled.set_child(self._list)
        self.append(scrolled)

        # Refresh button
        btn = Gtk.Button(label="Recarregar")
        btn.set_halign(Gtk.Align.END)
        btn.connect("clicked", lambda _b: self._refresh())
        self.append(btn)

        self._row_search_text: dict[Adw.ActionRow, str] = {}
        self._refresh()

    def _refresh(self) -> None:
        while child := self._list.get_first_child():
            self._list.remove(child)
        self._row_search_text.clear()

        ports = backend.list_ports()
        if not ports:
            empty = Adw.ActionRow()
            empty.set_title("Sem dados")
            empty.set_subtitle("semanage nao disponivel ou retornou vazio.")
            self._list.append(empty)
            return

        for p in sorted(ports, key=lambda x: x.context):
            row = Adw.ActionRow()
            row.set_title(p.context)
            row.set_subtitle(f"{p.proto.upper()}: {p.ports}")
            self._row_search_text[row] = (
                p.context.lower() + " " + p.proto.lower() + " " + p.ports.lower()
            )
            self._list.append(row)

    def _filter(self, row: Gtk.ListBoxRow) -> bool:
        query = self._search.get_text().lower().strip()
        if not query:
            return True
        haystack = self._row_search_text.get(row)
        if haystack is None:
            return True
        return query in haystack
