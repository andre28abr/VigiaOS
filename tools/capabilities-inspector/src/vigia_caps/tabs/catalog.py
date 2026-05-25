"""Tab Catalogo: lista das ~40 capabilities do Linux com descricao pt-BR."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from ..capabilities import CAPABILITIES, RISK_ORDER
from ._helpers import escape_markup, make_clamp, risk_css


RISK_FILTERS = [
    ("Todas", None),
    ("Apenas ALTO", "alto"),
    ("Apenas MEDIO", "medio"),
    ("Apenas BAIXO", "baixo"),
]


class CatalogTab(Adw.Bin):
    """Referencia das capabilities (read-only)."""

    def __init__(self) -> None:
        super().__init__()
        self._risk_filter: str | None = None

        # Header
        header_lbl = Gtk.Label(label=f"{len(CAPABILITIES)} Linux capabilities")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(4)

        header_desc = Gtk.Label(
            label=(
                "Referencia: cada capability + descricao + classe de risco. "
                "Ordem: ALTO -> MEDIO -> BAIXO (mais perigoso primeiro)."
            )
        )
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(12)

        # Filters
        self._search = Gtk.SearchEntry()
        self._search.set_placeholder_text("Buscar capability...")
        self._search.set_hexpand(True)
        self._search.connect("search-changed", lambda _e: self._rebuild())

        self._risk_combo = Gtk.DropDown.new_from_strings(
            [opt[0] for opt in RISK_FILTERS]
        )
        self._risk_combo.connect("notify::selected", self._on_risk_changed)

        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        filter_box.append(self._search)
        filter_box.append(self._risk_combo)
        filter_box.set_margin_bottom(12)

        # List
        self._list = Gtk.ListBox()
        self._list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list.add_css_class("boxed-list")

        # Layout
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(20)
        outer.set_margin_bottom(20)
        outer.set_margin_start(20)
        outer.set_margin_end(20)
        outer.append(header_lbl)
        outer.append(header_desc)
        outer.append(filter_box)
        outer.append(self._list)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

        self._rebuild()

    def _on_risk_changed(self, _combo, _pspec) -> None:
        idx = self._risk_combo.get_selected()
        self._risk_filter = RISK_FILTERS[idx][1] if 0 <= idx < len(RISK_FILTERS) else None
        self._rebuild()

    def _matches(self, cap, query: str) -> bool:
        if self._risk_filter and cap.risk != self._risk_filter:
            return False
        if not query:
            return True
        q = query.lower()
        return (
            q in cap.name.lower()
            or q in cap.short.lower()
            or q in cap.long.lower()
        )

    def _rebuild(self) -> None:
        # Clear
        child = self._list.get_first_child()
        while child is not None:
            self._list.remove(child)
            child = self._list.get_first_child()

        query = self._search.get_text().strip()
        # Filtra + ordena por risco (ALTO primeiro)
        sorted_caps = sorted(
            CAPABILITIES,
            key=lambda c: (RISK_ORDER.get(c.risk, 99), c.name),
        )
        visible = [c for c in sorted_caps if self._matches(c, query)]

        for cap in visible:
            self._list.append(self._build_row(cap))

    def _build_row(self, cap) -> Adw.ExpanderRow:
        row = Adw.ExpanderRow()
        row.set_title(cap.name)
        row.set_subtitle(cap.short)
        row.set_subtitle_lines(2)

        # Risk badge prefix
        badge = Gtk.Label(label=cap.risk.upper())
        badge.add_css_class("monospace")
        badge.add_css_class("caption-heading")
        badge.add_css_class(risk_css(cap.risk))
        badge.set_valign(Gtk.Align.CENTER)
        row.add_prefix(badge)

        # Long description
        long_row = Adw.PreferencesRow()
        long_lbl = Gtk.Label(label=cap.long)
        long_lbl.set_wrap(True)
        long_lbl.set_xalign(0)
        long_lbl.set_selectable(True)
        long_lbl.set_margin_start(12)
        long_lbl.set_margin_end(12)
        long_lbl.set_margin_top(8)
        long_lbl.set_margin_bottom(12)
        long_row.set_child(long_lbl)
        long_row.set_activatable(False)
        row.add_row(long_row)

        return row
