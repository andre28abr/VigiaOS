"""Tab Historico — lista scans anteriores em ~/.local/share/vigia-rootkit/scans/.

Cada entrada eh um JSON com findings, KPIs, timestamp. Click pra ver
detalhes (raw output, findings list).
"""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from ._helpers import make_clamp


class HistoryTab(Adw.Bin):
    def __init__(self) -> None:
        super().__init__()
        self._rows: list = []
        self._destroyed = False

        # Header
        header_lbl = Gtk.Label(label="Historico de scans")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(8)

        desc_lbl = Gtk.Label()
        desc_lbl.set_markup(
            "Cada scan eh salvo em <tt>~/.local/share/vigia-rootkit/scans/</tt> "
            "(mode 0600, owner-only — LGPD). Clique numa entrada para ver os "
            "findings detalhados e o output bruto."
        )
        desc_lbl.add_css_class("dim-label")
        desc_lbl.set_halign(Gtk.Align.START)
        desc_lbl.set_wrap(True)
        desc_lbl.set_xalign(0)
        desc_lbl.set_margin_bottom(20)

        # Refresh button
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_halign(Gtk.Align.END)
        action_box.set_margin_bottom(12)
        refresh_btn = Gtk.Button(label="Recarregar")
        refresh_btn.connect("clicked", lambda _b: self.refresh())
        action_box.append(refresh_btn)

        # List group
        self._list_group = Adw.PreferencesGroup()
        self._list_group.set_title("Scans recentes")

        # Layout
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_top(24)
        inner.set_margin_bottom(32)
        inner.set_margin_start(28)
        inner.set_margin_end(28)
        inner.append(header_lbl)
        inner.append(desc_lbl)
        inner.append(action_box)
        inner.append(self._list_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(inner))
        self.set_child(scrolled)

        self.connect("destroy", self._on_destroy)
        self.refresh()

    def _on_destroy(self, *_a) -> None:
        self._destroyed = True

    def refresh(self) -> None:
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        try:
            reports = backend.list_recent_reports(limit=30)
        except Exception as e:  # pylint: disable=broad-except
            print(f"[history] list_reports falhou: {e}", flush=True)
            reports = []
        GLib.idle_add(self._apply, reports)

    def _apply(self, reports: list[dict]) -> bool:
        if self._destroyed:
            return False
        # Limpa rows antigos
        for r in self._rows:
            self._list_group.remove(r)
        self._rows = []

        if not reports:
            row = Adw.ActionRow(title="Nenhum scan registrado ainda")
            row.set_subtitle(
                "Rode um scan em chkrootkit ou rkhunter para criar o primeiro."
            )
            row.add_css_class("dim-label")
            self._list_group.add(row)
            self._rows.append(row)
            return False

        for rep in reports:
            row = self._build_row(rep)
            self._list_group.add(row)
            self._rows.append(row)

        return False

    def _build_row(self, rep: dict) -> Adw.ExpanderRow:
        scanner = rep.get("scanner", "?")
        ts = rep.get("started_at", "")
        warnings = rep.get("warnings_count", 0)
        infected = rep.get("infected_count", 0)
        tests = rep.get("tests_run", 0)
        elapsed = rep.get("elapsed_sec", 0)
        cancelled = rep.get("cancelled", False)
        error = rep.get("error", "")

        row = Adw.ExpanderRow()
        row.set_title(f"{scanner} · {ts}")

        if cancelled:
            subtitle = "cancelado"
            severity_css = "dim-label"
        elif error:
            subtitle = f"erro: {error[:80]}"
            severity_css = "error"
        elif infected > 0:
            subtitle = f"{infected} infectado(s) · {warnings} warning(s)"
            severity_css = "error"
        elif warnings > 0:
            subtitle = f"{warnings} warning(s) · {tests} testes"
            severity_css = "warning"
        else:
            subtitle = f"limpo · {tests} testes · {elapsed:.0f}s"
            severity_css = "success"
        row.set_subtitle(subtitle)

        # Badge severity
        badge = Gtk.Label(label=severity_css)
        badge.add_css_class("caption")
        badge.add_css_class(severity_css)
        row.add_prefix(badge)

        # Findings detail
        findings = rep.get("findings", [])
        if findings:
            findings_label = Gtk.Label()
            text = "\n".join(
                f"  [{f.get('severity', '?')}] {f.get('test', '?')}: {f.get('detail', '')}"
                for f in findings[:30]
            )
            findings_label.set_text(text)
            findings_label.set_wrap(True)
            findings_label.set_xalign(0)
            findings_label.set_selectable(True)
            findings_label.add_css_class("monospace")
            findings_label.add_css_class("caption")
            findings_label.set_margin_start(12)
            findings_label.set_margin_end(12)
            findings_label.set_margin_top(8)
            findings_label.set_margin_bottom(8)
            findings_row = Adw.PreferencesRow()
            findings_row.set_child(findings_label)
            findings_row.set_activatable(False)
            row.add_row(findings_row)

        # Raw output (truncated preview)
        raw = rep.get("raw_output", "")
        if raw:
            raw_label = Gtk.Label()
            preview = raw[:4000]
            if len(raw) > 4000:
                preview += "\n... (truncado, veja arquivo completo)"
            raw_label.set_text(preview)
            raw_label.set_wrap(False)
            raw_label.set_xalign(0)
            raw_label.set_selectable(True)
            raw_label.add_css_class("monospace")
            raw_label.add_css_class("caption")
            raw_label.add_css_class("dim-label")
            raw_label.set_margin_start(12)
            raw_label.set_margin_end(12)
            raw_label.set_margin_bottom(12)
            raw_row = Adw.PreferencesRow()
            raw_row.set_child(raw_label)
            raw_row.set_activatable(False)
            row.add_row(raw_row)

        # File path
        if "_file" in rep:
            file_row = Adw.ActionRow(title="Arquivo")
            file_row.add_css_class("property")
            file_lbl = Gtk.Label(label=rep["_file"])
            file_lbl.add_css_class("monospace")
            file_lbl.add_css_class("caption")
            file_lbl.set_selectable(True)
            file_row.add_suffix(file_lbl)
            row.add_row(file_row)

        return row
