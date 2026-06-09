"""Tab Timeline: lista de eventos cronologicos com filtros + search."""

from __future__ import annotations

import json

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from ..backend import ActivityBundle, ActivityEvent, severity_at_least
from ..glossary import explain
from ._helpers import (
    escape_markup,
    make_clamp,
    severity_css,
    severity_label,
    severity_short,
    source_label,
)


SEVERITY_OPTIONS = [
    ("Tudo", None),
    ("Vale olhar+", "interesting"),
    ("Só atenção", "suspicious"),
]


class TimelineTab(Adw.Bin):
    """Lista cronologica de eventos."""

    def __init__(self) -> None:
        super().__init__()
        self._events: list[ActivityEvent] = []
        self._source_filter: str | None = None
        self._severity_filter: str | None = None

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
        self._header_desc.set_margin_bottom(12)

        # Filtros
        self._search = Gtk.SearchEntry()
        self._search.set_placeholder_text("Buscar em narrativa ou raw...")
        self._search.set_hexpand(True)
        self._search.connect("search-changed", lambda _e: self._rebuild())

        self._sev_combo = Gtk.DropDown.new_from_strings(
            [opt[0] for opt in SEVERITY_OPTIONS]
        )
        self._sev_combo.connect("notify::selected", self._on_sev_changed)

        self._src_combo = Gtk.DropDown.new_from_strings(["Todas as fontes"])
        self._src_combo.connect("notify::selected", self._on_src_changed)

        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        filter_box.append(self._search)
        filter_box.append(self._sev_combo)
        filter_box.append(self._src_combo)
        filter_box.set_margin_bottom(12)

        # List
        self._list = Gtk.ListBox()
        self._list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list.add_css_class("boxed-list")

        self._empty_state = Adw.StatusPage(
            title="Sem eventos",
            description="Clique 'Atualizar' no header para coletar logs.",
            icon_name="dialog-information-symbolic",
        )
        self._empty_state.set_vexpand(True)

        self._stack = Gtk.Stack()
        self._stack.add_named(self._list, "list")
        self._stack.add_named(self._empty_state, "empty")

        # Layout
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(20)
        outer.set_margin_bottom(20)
        outer.set_margin_start(20)
        outer.set_margin_end(20)
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

    def refresh(self, bundle: ActivityBundle) -> None:
        self._events = list(bundle.events)
        self._refresh_source_combo()
        self._rebuild()

    def _refresh_source_combo(self) -> None:
        sources = sorted({e.source for e in self._events})
        items = ["Todas as fontes"] + [source_label(s) for s in sources]
        model = Gtk.StringList.new(items)
        self._src_combo.set_model(model)
        self._src_combo.set_selected(0)
        self._src_codes = [None] + sources

    def _on_sev_changed(self, _combo, _pspec) -> None:
        idx = self._sev_combo.get_selected()
        self._severity_filter = SEVERITY_OPTIONS[idx][1] if 0 <= idx < len(SEVERITY_OPTIONS) else None
        self._rebuild()

    def _on_src_changed(self, _combo, _pspec) -> None:
        idx = self._src_combo.get_selected()
        codes = getattr(self, "_src_codes", [None])
        self._source_filter = codes[idx] if 0 <= idx < len(codes) else None
        self._rebuild()

    def _matches(self, e: ActivityEvent, query: str) -> bool:
        if self._source_filter and e.source != self._source_filter:
            return False
        if self._severity_filter and not severity_at_least(e.severity, self._severity_filter):
            return False
        if not query:
            return True
        q = query.lower()
        if q in e.narrative.lower():
            return True
        # busca em payload serializado
        try:
            payload_str = json.dumps(e.payload, ensure_ascii=False).lower()
            return q in payload_str
        except (TypeError, ValueError):
            return False

    def _rebuild(self) -> None:
        query = self._search.get_text().strip()
        visible = [e for e in self._events if self._matches(e, query)]

        # Clear
        child = self._list.get_first_child()
        while child is not None:
            self._list.remove(child)
            child = self._list.get_first_child()

        total = len(self._events)
        if total == 0:
            self._stack.set_visible_child_name("empty")
            self._header_label.set_label("—")
            self._header_desc.set_label("")
            return

        self._stack.set_visible_child_name("list")
        shown = len(visible)
        if shown == total:
            self._header_label.set_label(f"{total} eventos")
        else:
            self._header_label.set_label(f"{shown} de {total} eventos")

        # Contagens por severidade
        susp = sum(1 for e in self._events if e.severity == "suspicious")
        info = sum(1 for e in self._events if e.severity == "interesting")
        rout = sum(1 for e in self._events if e.severity == "routine")
        self._header_desc.set_label(
            f"{susp} {severity_short('suspicious')} · "
            f"{info} {severity_short('interesting')} · "
            f"{rout} {severity_short('routine')}"
        )

        # Limita 500 rows pra UI nao explodir
        max_show = 500
        for i, e in enumerate(visible):
            if i >= max_show:
                more_row = Adw.ActionRow(title=f"… e mais {len(visible) - max_show} eventos")
                more_row.add_css_class("dim-label")
                self._list.append(more_row)
                break
            self._list.append(self._build_row(e))

    def focus_source(self, code: str) -> None:
        """Seleciona uma fonte específica no filtro (chamado pela aba Fontes)."""
        codes = getattr(self, "_src_codes", [None])
        aliases = ({"journal", "journald"}
                   if code in ("journal", "journald") else {code})
        for i, c in enumerate(codes):
            if c in aliases:
                self._src_combo.set_selected(i)
                return
        self._src_combo.set_selected(0)  # fonte não presente → mostra todas

    def _build_row(self, e: ActivityEvent) -> Adw.ExpanderRow:
        row = Adw.ExpanderRow()
        row.set_title(escape_markup(e.narrative))
        row.set_use_markup(True)
        row.set_title_lines(2)

        # Fonte (prefixo) + severidade colorida (sufixo)
        src_badge = Gtk.Label(label=source_label(e.source))
        src_badge.add_css_class("caption-heading")
        src_badge.add_css_class("dim-label")
        src_badge.set_valign(Gtk.Align.CENTER)
        row.add_prefix(src_badge)

        sev_badge = Gtk.Label(label=severity_label(e.severity))
        sev_badge.add_css_class("caption-heading")
        sev_badge.add_css_class(severity_css(e.severity))
        sev_badge.set_valign(Gtk.Align.CENTER)
        row.add_suffix(sev_badge)

        row.set_subtitle(e.timestamp)

        # ---- Conteúdo expandido: EXPLICAÇÃO primeiro, técnico depois ----
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        exp = explain(e.source, e.narrative, e.payload)
        head = Gtk.Label()
        head.set_markup(f"<b>{escape_markup(exp.title)}</b>")
        head.set_xalign(0)
        head.set_wrap(True)
        box.append(head)
        for label, text in (("O que é", exp.what),
                            ("É normal?", exp.normal),
                            ("O que fazer", exp.action)):
            lbl = Gtk.Label()
            lbl.set_markup(f"<b>{label}:</b> {escape_markup(text)}")
            lbl.set_xalign(0)
            lbl.set_wrap(True)
            box.append(lbl)

        # Detalhes técnicos (JSON cru) colapsados — não assustam de cara.
        payload_buf = Gtk.TextBuffer()
        try:
            payload_buf.set_text(
                json.dumps(e.payload, indent=2, ensure_ascii=False))
        except (TypeError, ValueError):
            payload_buf.set_text(repr(e.payload))
        payload_view = Gtk.TextView(buffer=payload_buf)
        payload_view.set_editable(False)
        payload_view.set_cursor_visible(False)
        payload_view.set_monospace(True)
        payload_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        payload_view.add_css_class("dim-label")
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(100)
        scrolled.set_max_content_height(240)
        scrolled.set_child(payload_view)

        tech = Gtk.Expander(label="Ver detalhes técnicos")
        tech.set_margin_top(6)
        tech.set_child(scrolled)
        box.append(tech)

        content_row = Adw.PreferencesRow()
        content_row.set_child(box)
        content_row.set_activatable(False)
        row.add_row(content_row)

        return row
