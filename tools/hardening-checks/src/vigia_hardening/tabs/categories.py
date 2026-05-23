"""Tab Categorias: agrupa findings por categoria do Lynis."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from ..backend import Finding, LynisReport, category_label
from ._helpers import make_clamp


class CategoriesTab(Adw.Bin):
    """Mostra findings agrupados por categoria (PreferencesGroup por cat)."""

    def __init__(self) -> None:
        super().__init__()

        self._container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self._container.set_margin_top(20)
        self._container.set_margin_bottom(20)
        self._container.set_margin_start(20)
        self._container.set_margin_end(20)

        self._empty_state = Adw.StatusPage(
            title="Sem dados",
            description="Execute uma auditoria na aba 'Resumo' para popular esta lista.",
            icon_name="folder-symbolic",
        )

        self._stack = Gtk.Stack()
        self._stack.add_named(self._container, "list")
        self._stack.add_named(self._empty_state, "empty")

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(self._stack))
        self.set_child(scrolled)

    def refresh(self, report: LynisReport) -> None:
        # Limpa container
        child = self._container.get_first_child()
        while child is not None:
            self._container.remove(child)
            child = self._container.get_first_child()

        if not report.has_data() or (not report.warnings and not report.suggestions):
            self._stack.set_visible_child_name("empty")
            return

        # Agrupa por categoria
        cats: dict[str, dict[str, list[Finding]]] = {}
        for f in report.warnings:
            cats.setdefault(f.category, {"warnings": [], "suggestions": []})
            cats[f.category]["warnings"].append(f)
        for f in report.suggestions:
            cats.setdefault(f.category, {"warnings": [], "suggestions": []})
            cats[f.category]["suggestions"].append(f)

        # Ordena: primeiro categorias com warnings, depois alfabetica
        ordered = sorted(
            cats.items(),
            key=lambda kv: (-len(kv[1]["warnings"]), kv[0]),
        )

        for cat_code, buckets in ordered:
            group = self._build_category_group(cat_code, buckets["warnings"], buckets["suggestions"])
            self._container.append(group)

        self._stack.set_visible_child_name("list")

    def _build_category_group(
        self,
        cat_code: str,
        warnings: list[Finding],
        suggestions: list[Finding],
    ) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup()
        title = f"{cat_code} — {category_label(cat_code)}"
        group.set_title(title)

        parts: list[str] = []
        if warnings:
            parts.append(f"{len(warnings)} warning{'s' if len(warnings) > 1 else ''}")
        if suggestions:
            parts.append(f"{len(suggestions)} suggestion{'s' if len(suggestions) > 1 else ''}")
        group.set_description(" · ".join(parts))

        for f in warnings:
            group.add(self._build_row(f, severity="error"))
        for f in suggestions:
            group.add(self._build_row(f, severity="warning"))

        return group

    def _build_row(self, f: Finding, severity: str) -> Adw.ActionRow:
        row = Adw.ActionRow()
        row.set_title(_escape_for_markup(f.message))
        row.set_use_markup(True)
        row.set_subtitle(f.test_id)
        row.set_title_lines(3)

        badge_label = "!" if severity == "error" else "?"
        badge = Gtk.Label(label=badge_label)
        badge.add_css_class("monospace")
        badge.add_css_class("title-4")
        badge.add_css_class(severity)
        badge.set_valign(Gtk.Align.CENTER)
        row.add_prefix(badge)

        return row


def _escape_for_markup(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
