"""Tab Mudancas: lista de arquivos divergentes do baseline."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from ..backend import FileChange
from ._helpers import make_clamp


CHANGE_LABEL = {
    "added": "Adicionado",
    "removed": "Removido",
    "changed": "Modificado",
}

CHANGE_CSS = {
    "added": "success",
    "removed": "error",
    "changed": "warning",
}


PROP_LABELS = {
    "perms": "permissões",
    "uid": "uid",
    "gid": "gid",
    "size": "tamanho",
    "blocks": "blocks",
    "mtime": "mtime",
    "links": "links",
    "inode": "inode",
    "checksum": "hash",
    "size_grow": "size_grow",
    "inode_change": "inode_chg",
}


class ChangesTab(Adw.Bin):
    """Lista filtravel de mudancas detectadas pelo ultimo check."""

    def __init__(self) -> None:
        super().__init__()
        self._changes: list[FileChange] = []
        self._type_filter: str | None = None

        # Header
        self._header_label = Gtk.Label(label="—")
        self._header_label.add_css_class("title-2")
        self._header_label.set_halign(Gtk.Align.START)
        self._header_label.set_margin_bottom(4)

        self._header_desc = Gtk.Label(label="")
        self._header_desc.add_css_class("dim-label")
        self._header_desc.set_halign(Gtk.Align.START)
        self._header_desc.set_wrap(True)
        self._header_desc.set_xalign(0)
        self._header_desc.set_margin_bottom(24)

        # Filtros
        self._search = Gtk.SearchEntry()
        self._search.set_placeholder_text("Buscar por path...")
        self._search.set_hexpand(True)
        self._search.connect("search-changed", lambda _e: self._rebuild())

        self._type_combo = Gtk.DropDown.new_from_strings(
            ["Todas", "Adicionadas", "Removidas", "Modificadas"]
        )
        self._type_combo.connect("notify::selected", self._on_type_changed)

        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        filter_box.append(self._search)
        filter_box.append(self._type_combo)
        filter_box.set_margin_bottom(12)

        # List
        self._list = Gtk.ListBox()
        self._list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list.add_css_class("boxed-list")

        self._empty_state = Adw.StatusPage(
            title="Sem mudanças",
            description="Execute uma verificação na aba 'Status' para popular esta lista.",
            icon_name="dialog-information-symbolic",
        )
        self._empty_state.set_vexpand(True)

        self._stack = Gtk.Stack()
        self._stack.add_named(self._list, "list")
        self._stack.add_named(self._empty_state, "empty")

        # Layout
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(24)
        outer.set_margin_bottom(32)
        outer.set_margin_start(28)
        outer.set_margin_end(28)
        outer.append(self._header_label)
        outer.append(self._header_desc)
        outer.append(filter_box)
        outer.append(self._stack)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

    # ============================================================

    def refresh(self, changes: list[FileChange]) -> None:
        self._changes = changes
        self._rebuild()

    def _on_type_changed(self, _combo, _pspec) -> None:
        idx = self._type_combo.get_selected()
        self._type_filter = (None, "added", "removed", "changed")[idx]
        self._rebuild()

    def _matches(self, c: FileChange, query: str) -> bool:
        if self._type_filter and c.change_type != self._type_filter:
            return False
        if not query:
            return True
        q = query.lower()
        return q in c.path.lower()

    def _rebuild(self) -> None:
        query = self._search.get_text().strip()
        visible = [c for c in self._changes if self._matches(c, query)]

        # Clear
        child = self._list.get_first_child()
        while child is not None:
            self._list.remove(child)
            child = self._list.get_first_child()

        total = len(self._changes)
        if total == 0:
            self._stack.set_visible_child_name("empty")
            self._header_label.set_label("Sem mudanças")
            self._header_desc.set_label("")
            return

        shown = len(visible)
        self._stack.set_visible_child_name("list")
        if shown == total:
            self._header_label.set_label(f"{total} {'mudança' if total == 1 else 'mudanças'}")
        else:
            self._header_label.set_label(f"{shown} de {total} mudanças")

        added = sum(1 for c in self._changes if c.change_type == "added")
        removed = sum(1 for c in self._changes if c.change_type == "removed")
        changed = sum(1 for c in self._changes if c.change_type == "changed")
        parts = []
        if added: parts.append(f"{added} adicionada{'s' if added > 1 else ''}")
        if removed: parts.append(f"{removed} removida{'s' if removed > 1 else ''}")
        if changed: parts.append(f"{changed} modificada{'s' if changed > 1 else ''}")
        self._header_desc.set_label(" · ".join(parts) if parts else "")

        for c in visible:
            self._list.append(self._build_row(c))

    def _build_row(self, c: FileChange) -> Gtk.ListBoxRow:
        row = Adw.ActionRow()
        row.set_title(_escape(c.path))
        row.set_use_markup(True)
        row.set_title_lines(2)

        # Badge
        badge = Gtk.Label(label=CHANGE_LABEL.get(c.change_type, c.change_type))
        badge.add_css_class("caption-heading")
        badge.add_css_class(CHANGE_CSS.get(c.change_type, "dim-label"))
        badge.set_valign(Gtk.Align.CENTER)
        row.add_prefix(badge)

        # Subtitle: propriedades modificadas
        if c.properties:
            props_labels = [PROP_LABELS.get(p, p) for p in c.properties]
            row.set_subtitle("Alterado: " + ", ".join(props_labels))

        # Copy button
        copy_btn = Gtk.Button.new_from_icon_name("edit-copy-symbolic")
        copy_btn.set_valign(Gtk.Align.CENTER)
        copy_btn.add_css_class("flat")
        copy_btn.set_tooltip_text(f"Copiar caminho")
        copy_btn.connect("clicked", self._on_copy, c.path)
        row.add_suffix(copy_btn)

        return row

    def _on_copy(self, _btn: Gtk.Button, path: str) -> None:
        display = self.get_display()
        if display is not None:
            display.get_clipboard().set(path)


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
