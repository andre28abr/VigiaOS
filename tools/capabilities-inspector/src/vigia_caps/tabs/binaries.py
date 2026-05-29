"""Tab Binarios: lista filtravel dos binarios com capabilities."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .. import backend
from ..capabilities import get_capability, risk_for_cap
from ._helpers import escape_markup, make_clamp, risk_css


RISK_FILTERS = [
    ("Todos os riscos", None),
    ("Apenas ALTO", "alto"),
    ("Apenas MÉDIO", "medio"),
    ("Apenas BAIXO", "baixo"),
]


class BinariesTab(Adw.Bin):
    """Lista filtravel dos binarios + suas caps."""

    def __init__(self) -> None:
        super().__init__()
        self._binaries: list[backend.BinaryWithCaps] = []
        self._risk_filter: str | None = None

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
        self._search.set_placeholder_text("Buscar por path ou capability...")
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

        self._empty_state = Adw.StatusPage(
            title="Sem scan",
            description="Vá para a aba 'Visão Geral' e clique 'Escanear' para popular.",
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
    # API
    # ============================================================

    def refresh(self, binaries: list[backend.BinaryWithCaps]) -> None:
        self._binaries = list(binaries)
        # Ordena: primeiro ALTO, depois MEDIO, depois BAIXO
        self._binaries.sort(
            key=lambda b: (
                self._max_risk_score(b),
                b.path,
            )
        )
        self._rebuild()

    def _max_risk_score(self, binary: backend.BinaryWithCaps) -> int:
        """Quanto menor, mais alto risco (pra ordenar em ordem decrescente)."""
        scores = {"alto": 0, "medio": 1, "baixo": 2, "desconhecida": 3}
        score = 3
        for cap_name in binary.cap_names:
            r = risk_for_cap(cap_name)
            score = min(score, scores.get(r, 3))
        return score

    def _on_risk_changed(self, _combo, _pspec) -> None:
        idx = self._risk_combo.get_selected()
        self._risk_filter = RISK_FILTERS[idx][1] if 0 <= idx < len(RISK_FILTERS) else None
        self._rebuild()

    def _matches(self, b: backend.BinaryWithCaps, query: str) -> bool:
        if self._risk_filter:
            # Filtra se PELO MENOS UMA capability bate com o risk filter
            risks = {risk_for_cap(c) for c in b.cap_names}
            if self._risk_filter not in risks:
                return False
        if not query:
            return True
        q = query.lower()
        if q in b.path.lower():
            return True
        for cap_name in b.cap_names:
            if q in cap_name.lower():
                return True
        return False

    def _rebuild(self) -> None:
        query = self._search.get_text().strip()
        visible = [b for b in self._binaries if self._matches(b, query)]

        # Clear
        child = self._list.get_first_child()
        while child is not None:
            self._list.remove(child)
            child = self._list.get_first_child()

        total = len(self._binaries)
        if total == 0:
            self._stack.set_visible_child_name("empty")
            self._header_label.set_label("Sem scan")
            self._header_desc.set_label("")
            return

        self._stack.set_visible_child_name("list")
        shown = len(visible)
        if shown == total:
            self._header_label.set_label(
                f"{total} {'binário' if total == 1 else 'binários'}"
            )
        else:
            self._header_label.set_label(f"{shown} de {total} binários")

        # Contagem por risco
        risk_count = {"alto": 0, "medio": 0, "baixo": 0}
        for b in self._binaries:
            highest = self._highest_risk(b)
            if highest in risk_count:
                risk_count[highest] += 1
        parts: list[str] = []
        if risk_count["alto"]:
            parts.append(f"{risk_count['alto']} ALTO")
        if risk_count["medio"]:
            parts.append(f"{risk_count['medio']} médio")
        if risk_count["baixo"]:
            parts.append(f"{risk_count['baixo']} baixo")
        self._header_desc.set_label(" · ".join(parts) if parts else "")

        # Build rows
        for b in visible:
            self._list.append(self._build_row(b))

    def _highest_risk(self, binary: backend.BinaryWithCaps) -> str:
        """Retorna o risco mais alto entre as caps do binario."""
        risks = {risk_for_cap(c) for c in binary.cap_names}
        if "alto" in risks:
            return "alto"
        if "medio" in risks:
            return "medio"
        if "baixo" in risks:
            return "baixo"
        return "desconhecida"

    def _build_row(self, binary: backend.BinaryWithCaps) -> Adw.ExpanderRow:
        row = Adw.ExpanderRow()
        row.set_title(escape_markup(binary.path))
        row.set_use_markup(True)
        row.set_subtitle(", ".join(binary.cap_names))
        row.set_subtitle_lines(2)

        # Highest risk badge as prefix
        highest = self._highest_risk(binary)
        badge = Gtk.Label(label=highest.upper())
        badge.add_css_class("monospace")
        badge.add_css_class("caption-heading")
        badge.add_css_class(risk_css(highest))
        badge.set_valign(Gtk.Align.CENTER)
        row.add_prefix(badge)

        # Copy button
        copy_btn = Gtk.Button.new_from_icon_name("edit-copy-symbolic")
        copy_btn.set_valign(Gtk.Align.CENTER)
        copy_btn.add_css_class("flat")
        copy_btn.set_tooltip_text("Copiar path")
        copy_btn.connect("clicked", self._on_copy_clicked, binary.path)
        row.add_suffix(copy_btn)

        # Per-cap rows (expandido)
        for cap_name in binary.cap_names:
            cap_info = get_capability(cap_name)
            cap_row = Adw.ActionRow()
            cap_row.set_title(cap_name)
            if cap_info:
                cap_row.set_subtitle(cap_info.short)
                cap_row.set_subtitle_lines(2)
                # Risk badge no cap row
                cap_badge = Gtk.Label(label=cap_info.risk.upper())
                cap_badge.add_css_class("monospace")
                cap_badge.add_css_class("caption")
                cap_badge.add_css_class(risk_css(cap_info.risk))
                cap_badge.set_valign(Gtk.Align.CENTER)
                cap_row.add_suffix(cap_badge)
            else:
                cap_row.set_subtitle("(capability desconhecida — ver docs)")
            row.add_row(cap_row)

        # Raw capabilities string
        raw_row = Adw.ActionRow(title="Raw")
        raw_row.add_css_class("property")
        raw_lbl = Gtk.Label(label=", ".join(binary.capabilities))
        raw_lbl.add_css_class("monospace")
        raw_lbl.add_css_class("caption")
        raw_lbl.set_selectable(True)
        raw_row.add_suffix(raw_lbl)
        row.add_row(raw_row)

        return row

    def _on_copy_clicked(self, _btn: Gtk.Button, path: str) -> None:
        display = self.get_display()
        if display is not None:
            display.get_clipboard().set(path)
