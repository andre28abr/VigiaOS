"""Tab Processes: contextos SELinux de processos rodando (read-only)."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .. import backend


class ProcessesTab(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL, spacing=8,
            margin_top=12, margin_bottom=12, margin_start=12, margin_end=12,
        )

        intro = Gtk.Label()
        intro.set_markup(
            "<b>Contextos SELinux dos processos</b> — cada processo roda dentro de um "
            "dominio SELinux. Util para entender que regras se aplicam a cada app."
        )
        intro.set_wrap(True)
        intro.set_xalign(0)
        self.append(intro)

        self._search = Gtk.SearchEntry()
        self._search.set_placeholder_text("Filtrar por comm, user ou contexto (ex: httpd, root, init)")
        self._search.connect("search-changed", lambda _e: self._list.invalidate_filter())
        self.append(self._search)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self._list = Gtk.ListBox()
        self._list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list.add_css_class("boxed-list")
        self._list.set_filter_func(self._filter)
        scrolled.set_child(self._list)
        self.append(scrolled)

        btn = Gtk.Button(label="Atualizar")
        btn.set_halign(Gtk.Align.END)
        btn.connect("clicked", lambda _b: self._refresh())
        self.append(btn)

        self._row_search_text: dict[Adw.ActionRow, str] = {}
        self._refresh()

    def _refresh(self) -> None:
        while child := self._list.get_first_child():
            self._list.remove(child)
        self._row_search_text.clear()

        procs = backend.list_processes(limit=300)
        if not procs:
            empty = Adw.ActionRow()
            empty.set_title("Sem dados")
            empty.set_subtitle("ps -eZ retornou vazio.")
            self._list.append(empty)
            return

        for p in procs:
            row = Adw.ActionRow()
            row.set_title(f"{p.comm} (pid {p.pid})")
            # Extrai so o type do contexto (parte central)
            short = p.context.split(":")[2] if p.context.count(":") >= 2 else p.context
            row.set_subtitle(f"user={p.user}  type={short}")
            self._row_search_text[row] = (
                p.comm.lower() + " " + p.user.lower() + " " + p.context.lower()
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
