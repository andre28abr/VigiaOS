"""Seção Relatórios do VigiaOS — visão por período do banco de eventos.

Lê `vigia_common.events` (achados gravados pelas ferramentas) e mostra, por
período: um resumo (total + por severidade + por fonte), a lista de eventos, e
ações de **exportar** (HTML com selo SHA-256, imprimível) e **limpar histórico**
(retenção / LGPD). `build_content()` é embarcado pelo window como seção do rail.

GTK só aqui; geração do HTML e rótulos vêm do `reports_html` (puro/testado).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from vigia_common import events  # noqa: E402

from .reports_html import build_html  # noqa: E402
from .reports_html import sev_label as _sev  # noqa: E402
from .reports_html import src_label as _src_label  # noqa: E402

# (rótulo, dias) — None = tudo
_PERIODS = [
    ("Últimos 7 dias", 7),
    ("Últimos 30 dias", 30),
    ("Últimos 90 dias", 90),
    ("Último ano", 365),
    ("Tudo", None),
]
_DEFAULT_PERIOD = 1   # "Últimos 30 dias"


def _period_range(days):
    if days is None:
        return None, None
    end = datetime.now()
    return end - timedelta(days=days), end


def build_content() -> Gtk.Widget:
    view = _ReportsView()
    overlay = Adw.ToastOverlay()
    overlay.set_child(view)
    view.set_toast_overlay(overlay)

    header = Adw.HeaderBar()
    header.set_title_widget(Adw.WindowTitle(
        title="Relatórios", subtitle="Eventos de segurança por período"))

    tv = Adw.ToolbarView()
    tv.add_top_bar(header)
    tv.set_content(overlay)
    return tv


class _ReportsView(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._toast_overlay: Adw.ToastOverlay | None = None
        self._last_label = ""
        self._last_events: list = []
        self._last_summary: dict = {}

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.append(scrolled)
        page = Adw.PreferencesPage()
        scrolled.set_child(page)

        # --- Período (+ Exportar) ---
        g_period = Adw.PreferencesGroup()
        self._combo = Adw.ComboRow()
        self._combo.set_title("Período")
        self._combo.add_prefix(
            Gtk.Image.new_from_icon_name("x-office-calendar-symbolic"))
        model = Gtk.StringList()
        for label, _d in _PERIODS:
            model.append(label)
        self._combo.set_model(model)
        self._combo.set_selected(_DEFAULT_PERIOD)
        self._combo.connect("notify::selected", lambda *_a: self._refresh())
        export = Gtk.Button(label="Exportar")
        export.add_css_class("flat")
        export.set_valign(Gtk.Align.CENTER)
        export.connect("clicked", self._on_export)
        self._combo.add_suffix(export)
        g_period.add(self._combo)
        page.add(g_period)

        # --- Resumo ---
        self._g_summary = Adw.PreferencesGroup()
        self._g_summary.set_title("Resumo")
        page.add(self._g_summary)
        self._summary_rows: list[Gtk.Widget] = []

        # --- Eventos ---
        self._g_events = Adw.PreferencesGroup()
        self._g_events.set_title("Eventos")
        page.add(self._g_events)
        self._event_rows: list[Gtk.Widget] = []

        # --- Manutenção ---
        g_admin = Adw.PreferencesGroup()
        clear = Adw.ActionRow()
        clear.set_title("Limpar histórico")
        clear.set_subtitle(
            "Apaga TODOS os eventos guardados. Relatórios já exportados não são "
            "afetados. (Retenção automática: 180 dias.)")
        clear.set_subtitle_lines(0)
        clear.add_prefix(Gtk.Image.new_from_icon_name("user-trash-symbolic"))
        clear_btn = Gtk.Button(label="Limpar")
        clear_btn.add_css_class("destructive-action")
        clear_btn.set_valign(Gtk.Align.CENTER)
        clear_btn.connect("clicked", self._on_clear)
        clear.add_suffix(clear_btn)
        g_admin.add(clear)
        page.add(g_admin)

        self.connect("map", lambda *_a: self._refresh())
        self._refresh()

    def set_toast_overlay(self, overlay: Adw.ToastOverlay) -> None:
        self._toast_overlay = overlay

    def _toast(self, text: str) -> None:
        if self._toast_overlay is not None:
            self._toast_overlay.add_toast(Adw.Toast.new(text))

    def _clear(self, group, rows: list) -> None:
        for r in rows:
            group.remove(r)
        rows.clear()

    def _detail(self, title: str, value: str) -> Adw.ActionRow:
        r = Adw.ActionRow()
        r.set_title(title)
        r.set_subtitle(value)
        r.set_subtitle_lines(0)
        r.set_subtitle_selectable(True)
        return r

    # -- refresh --
    def _refresh(self) -> None:
        idx = self._combo.get_selected()
        label, days = (_PERIODS[idx] if 0 <= idx < len(_PERIODS)
                       else _PERIODS[_DEFAULT_PERIOD])
        start, end = _period_range(days)
        summary = events.summary(start=start, end=end)
        evs = events.query(start=start, end=end, limit=300)
        self._last_label, self._last_summary, self._last_events = label, summary, evs
        self._render_summary(summary)
        self._render_events(evs)

    def _render_summary(self, summary: dict) -> None:
        self._clear(self._g_summary, self._summary_rows)
        total = summary.get("total", 0)

        if total == 0:
            empty = Adw.ActionRow()
            empty.set_title("Nenhum evento neste período.")
            empty.set_subtitle(
                "Rode uma varredura (Antivírus, Vuln Scanner, Rootkit…) e volte aqui.")
            empty.set_subtitle_lines(0)
            empty.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
            self._g_summary.add(empty)
            self._summary_rows.append(empty)
            return

        total_row = Adw.ActionRow()
        total_row.set_title(f"{total} evento(s) no período")
        total_row.add_prefix(Gtk.Image.new_from_icon_name("view-list-symbolic"))
        self._g_summary.add(total_row)
        self._summary_rows.append(total_row)

        by_sev = summary.get("by_severity", {})
        sev_parts = [f"{by_sev[s]} {_sev(s)[0].lower()}"
                     for s in events.CANON_SEVERITIES if by_sev.get(s)]
        if sev_parts:
            row = Adw.ActionRow()
            row.set_title("Por severidade")
            row.set_subtitle(" · ".join(sev_parts))
            row.set_subtitle_lines(0)
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
            self._g_summary.add(row)
            self._summary_rows.append(row)

        by_src = summary.get("by_source", {})
        if by_src:
            src_parts = [f"{_src_label(s)}: {n}"
                         for s, n in sorted(by_src.items(), key=lambda kv: -kv[1])]
            row = Adw.ActionRow()
            row.set_title("Por ferramenta")
            row.set_subtitle(" · ".join(src_parts))
            row.set_subtitle_lines(0)
            row.add_prefix(
                Gtk.Image.new_from_icon_name("applications-utilities-symbolic"))
            self._g_summary.add(row)
            self._summary_rows.append(row)

    def _render_events(self, evs: list) -> None:
        self._clear(self._g_events, self._event_rows)
        if not evs:
            self._g_events.set_description(None)
            return
        self._g_events.set_description(
            f"{len(evs)} evento(s) — mais recentes primeiro.")
        for e in evs:
            label, css = _sev(e.severity)
            exp = Adw.ExpanderRow()
            exp.set_title(e.title)
            exp.set_subtitle(f"{_src_label(e.source)} · {e.ts}")
            exp.set_subtitle_lines(0)
            badge = Gtk.Label(label=label)
            badge.add_css_class("caption")
            if css in ("error", "warning", "success"):
                badge.add_css_class(css)
            badge.set_valign(Gtk.Align.CENTER)
            exp.add_suffix(badge)
            if e.detail:
                exp.add_row(self._detail("Detalhe", e.detail))
            if e.ref:
                exp.add_row(self._detail("Onde", e.ref))
            self._g_events.add(exp)
            self._event_rows.append(exp)

    # -- exportar (HTML com selo SHA-256) --
    def _on_export(self, _btn) -> None:
        if not self._last_events and not self._last_summary.get("total"):
            self._toast("Nada pra exportar neste período.")
            return
        dialog = Gtk.FileDialog()
        stamp = datetime.now().strftime("%Y-%m-%d")
        dialog.set_initial_name(f"vigia-relatorio-{stamp}.html")
        dialog.save(self.get_root(), None, self._on_export_done)

    def _on_export_done(self, dialog, result) -> None:
        try:
            gfile = dialog.save_finish(result)
        except GLib.Error:
            return
        if gfile is None:
            return
        try:
            html = build_html(self._last_label, self._last_summary,
                              self._last_events)
            Path(gfile.get_path()).write_text(html, encoding="utf-8")
            self._toast("Relatório exportado.")
        except OSError as e:
            print(f"[relatorios] export falhou: {e}", flush=True)

    # -- limpar histórico --
    def _on_clear(self, _btn) -> None:
        dialog = Adw.AlertDialog(
            heading="Limpar histórico de eventos?",
            body="Isso apaga TODOS os eventos guardados no banco. Os relatórios "
                 "já exportados em arquivos não são afetados. Não dá pra desfazer.")
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("clear", "Limpar tudo")
        dialog.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_clear_response)
        dialog.present(self.get_root())

    def _on_clear_response(self, _dialog, response: str) -> None:
        if response == "clear":
            n = events.purge_all()
            self._toast(f"{n} evento(s) apagado(s).")
            self._refresh()
