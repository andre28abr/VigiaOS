"""Tab Historico — lista scans anteriores em formato PreferencesPage."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend


class HistoryTab(Adw.Bin):
    """Lista de scans em Adw.PreferencesPage (auto-clamped)."""

    def __init__(self) -> None:
        super().__init__()
        self._destroyed = False
        self._rows: list = []

        self._page = Adw.PreferencesPage()
        self._page.set_title("Historico de scans")

        self._list_group = Adw.PreferencesGroup()
        self._list_group.set_title("Scans recentes")
        self._list_group.set_description(
            "Cada scan eh salvo em ~/.local/share/vigia-rootkit/scans/ "
            "(mode 0600 — owner-only)."
        )
        self._page.add(self._list_group)

        self.set_child(self._page)
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
            print(f"[history] falhou: {e}", flush=True)
            reports = []
        GLib.idle_add(self._apply, reports)

    def _apply(self, reports: list[dict]) -> bool:
        if self._destroyed:
            return False
        for r in self._rows:
            self._list_group.remove(r)
        self._rows = []

        if not reports:
            row = Adw.ActionRow(title="Nenhum scan registrado ainda")
            row.set_subtitle(
                "Rode um scan em chkrootkit ou Rootkit Hunter pra criar o primeiro."
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

    def _build_row(self, rep: dict) -> Adw.ActionRow:
        scanner = rep.get("scanner", "?")
        ts = rep.get("started_at", "")
        warnings = rep.get("warnings_count", 0)
        infected = rep.get("infected_count", 0)
        tests = rep.get("tests_run", 0)
        elapsed = rep.get("elapsed_sec", 0)
        cancelled = rep.get("cancelled", False)
        error = rep.get("error", "")

        row = Adw.ActionRow()
        row.set_title(f"{scanner} · {ts}")

        if cancelled:
            subtitle = "cancelado"
        elif error:
            subtitle = f"erro: {error[:80]}"
        elif infected > 0:
            subtitle = f"{infected} infectado(s) · {warnings} warning(s)"
        elif warnings > 0:
            subtitle = f"{warnings} warning(s) · {tests} testes"
        else:
            subtitle = f"limpo · {tests} testes · {elapsed:.0f}s"
        row.set_subtitle(subtitle)

        # Badge no suffix
        if infected > 0:
            badge = Gtk.Label(label="INFECTADO")
            badge.add_css_class("error")
        elif warnings > 0:
            badge = Gtk.Label(label="warning")
            badge.add_css_class("warning")
        elif cancelled:
            badge = Gtk.Label(label="cancelado")
            badge.add_css_class("dim-label")
        else:
            badge = Gtk.Label(label="limpo")
            badge.add_css_class("success")
        badge.add_css_class("caption")
        row.add_suffix(badge)

        return row
