"""Tab Warnings: lista de findings criticos do Lynis."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from ..backend import Finding, LynisReport, category_label
from ._helpers import make_clamp


class FindingsListTab(Adw.Bin):
    """Base: lista filtravel de findings (warnings ou suggestions)."""

    SEVERITY_CSS = "error"  # subclasse override
    EMPTY_TITLE = "Sem findings"
    EMPTY_DESC = ""
    EMPTY_ICON = "dialog-information-symbolic"

    def __init__(self) -> None:
        super().__init__()
        self._findings: list[Finding] = []
        self._category_filter: str | None = None

        # ---- Header ---- #
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

        # ---- Search + filter ---- #
        self._search = Gtk.SearchEntry()
        self._search.set_placeholder_text("Buscar por mensagem ou test-id...")
        self._search.set_hexpand(True)
        self._search.connect("search-changed", lambda _e: self._rebuild())

        self._category_combo = Gtk.DropDown.new_from_strings(["Todas as categorias"])
        self._category_combo.connect("notify::selected", self._on_category_changed)

        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        filter_box.append(self._search)
        filter_box.append(self._category_combo)
        filter_box.set_margin_bottom(12)

        # ---- ListBox ---- #
        self._list = Gtk.ListBox()
        self._list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list.add_css_class("boxed-list")

        # Empty state
        self._empty_state = Adw.StatusPage(
            title=self.EMPTY_TITLE,
            description=self.EMPTY_DESC,
            icon_name=self.EMPTY_ICON,
        )
        self._empty_state.set_vexpand(True)

        self._stack = Gtk.Stack()
        self._stack.add_named(self._list, "list")
        self._stack.add_named(self._empty_state, "empty")

        # ---- Layout ---- #
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
    # API
    # ============================================================

    def refresh(self, report: LynisReport) -> None:
        self._findings = self._extract_findings(report)
        self._refresh_categories()
        self._rebuild()

    def _extract_findings(self, report: LynisReport) -> list[Finding]:
        """Subclasses override para retornar warnings ou suggestions."""
        return []

    # ============================================================
    # Internal
    # ============================================================

    def _refresh_categories(self) -> None:
        cats = sorted({f.category for f in self._findings})
        items = ["Todas as categorias"] + [f"{c} — {category_label(c)}" for c in cats]
        # Reconstroi o DropDown (jeito mais simples)
        new_model = Gtk.StringList.new(items)
        self._category_combo.set_model(new_model)
        self._category_combo.set_selected(0)
        self._category_codes = [None] + cats  # paralelo a items

    def _on_category_changed(self, _combo, _pspec) -> None:
        idx = self._category_combo.get_selected()
        codes = getattr(self, "_category_codes", [None])
        self._category_filter = codes[idx] if 0 <= idx < len(codes) else None
        self._rebuild()

    def _matches(self, f: Finding, query: str) -> bool:
        if self._category_filter and f.category != self._category_filter:
            return False
        if not query:
            return True
        q = query.lower()
        return (
            q in f.message.lower()
            or q in f.test_id.lower()
            or q in f.category.lower()
            or q in category_label(f.category).lower()
        )

    def _rebuild(self) -> None:
        query = self._search.get_text().strip()
        visible = [f for f in self._findings if self._matches(f, query)]

        # Clear list
        child = self._list.get_first_child()
        while child is not None:
            self._list.remove(child)
            child = self._list.get_first_child()

        # Header
        total = len(self._findings)
        shown = len(visible)
        if total == 0:
            self._stack.set_visible_child_name("empty")
            self._header_label.set_label("Nenhum finding")
            self._header_desc.set_label(self.EMPTY_DESC)
            return

        self._stack.set_visible_child_name("list")
        if shown == total:
            self._header_label.set_label(f"{total} {'item' if total == 1 else 'itens'}")
        else:
            self._header_label.set_label(f"{shown} de {total} {'item' if total == 1 else 'itens'}")

        for f in visible:
            self._list.append(self._build_row(f))

    def _build_row(self, f: Finding) -> Gtk.ListBoxRow:
        row = Adw.ActionRow()
        row.set_title(_escape_for_markup(f.message))
        row.set_use_markup(True)
        row.set_subtitle(f"{f.test_id} · {category_label(f.category)}")
        row.set_title_lines(3)

        # Badge prefix com categoria
        badge = Gtk.Label(label=f.category)
        badge.add_css_class("monospace")
        badge.add_css_class("caption-heading")
        badge.add_css_class(self.SEVERITY_CSS)
        badge.set_valign(Gtk.Align.CENTER)
        row.add_prefix(badge)

        # Copy button suffix
        copy_btn = Gtk.Button.new_from_icon_name("edit-copy-symbolic")
        copy_btn.set_valign(Gtk.Align.CENTER)
        copy_btn.add_css_class("flat")
        copy_btn.set_tooltip_text(f"Copiar {f.test_id}")
        copy_btn.connect("clicked", self._on_copy_clicked, f.test_id)
        row.add_suffix(copy_btn)

        return row

    def _on_copy_clicked(self, _btn: Gtk.Button, test_id: str) -> None:
        display = self.get_display()
        if display is not None:
            display.get_clipboard().set(test_id)


def _escape_for_markup(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class WarningsTab(FindingsListTab):
    SEVERITY_CSS = "error"
    EMPTY_TITLE = "Sem warnings"
    EMPTY_DESC = "Nenhuma crítica encontrada. Execute uma auditoria na aba 'Resumo'."

    def _extract_findings(self, report: LynisReport) -> list[Finding]:
        return list(report.warnings)


# Backwards compat (caso algum lugar importe)
__all__ = ["FindingsListTab", "WarningsTab"]
