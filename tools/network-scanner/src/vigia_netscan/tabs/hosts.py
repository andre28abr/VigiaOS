"""Tab Hosts: historico de scans + hosts descobertos cumulativos."""

from __future__ import annotations

import threading
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from ._helpers import make_clamp


class HostsTab(Adw.Bin):
    """Historico de scans com hosts encontrados."""

    def __init__(self) -> None:
        super().__init__()

        # Header
        header_lbl = Gtk.Label(label="Historico de scans")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(4)

        header_desc = Gtk.Label(
            label=(
                "Arquivos JSON em <tt>~/.local/share/vigia-netscan/</tt> "
                "com permissoes 0600 (apenas voce le)."
            )
        )
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(16)
        header_desc.set_use_markup(True)

        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toolbar.set_margin_bottom(16)
        self._refresh_btn = Gtk.Button(label="Recarregar")
        self._refresh_btn.connect("clicked", lambda _b: self.refresh())
        toolbar.append(self._refresh_btn)

        # Hosts group
        self._scans_group = Adw.PreferencesGroup()
        self._scans_group.set_title("Scans realizados")
        self._scan_rows: list = []

        self._status_lbl = Gtk.Label(label="")
        self._status_lbl.add_css_class("dim-label")
        self._status_lbl.set_halign(Gtk.Align.START)

        # Layout
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(20)
        outer.set_margin_bottom(20)
        outer.set_margin_start(20)
        outer.set_margin_end(20)
        outer.append(header_lbl)
        outer.append(header_desc)
        outer.append(toolbar)
        outer.append(self._scans_group)
        outer.append(self._status_lbl)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

        self.refresh()

    def refresh(self) -> None:
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        scans = backend.list_recent_scans(limit=30)
        GLib.idle_add(self._apply, scans)

    def _apply(self, scans: list[dict]) -> bool:
        for r in self._scan_rows:
            self._scans_group.remove(r)
        self._scan_rows = []

        if not scans:
            row = Adw.ActionRow(title="Nenhum scan realizado ainda")
            row.set_subtitle("Va a aba 'Scan' para realizar um.")
            row.add_css_class("dim-label")
            self._scans_group.add(row)
            self._scan_rows.append(row)
            self._status_lbl.set_label("")
            return False

        unique_addrs = set()
        for scan in scans:
            for h in scan.get("hosts", []):
                if h.get("status") == "up" and h.get("address"):
                    unique_addrs.add(h["address"])

        self._status_lbl.set_label(
            f"{len(scans)} scan{'s' if len(scans) != 1 else ''} no historico · "
            f"{len(unique_addrs)} host{'s' if len(unique_addrs) != 1 else ''} unico{'s' if len(unique_addrs) != 1 else ''} descoberto{'s' if len(unique_addrs) != 1 else ''}."
        )

        for scan in scans:
            ts = scan.get("started_at", "?")
            try:
                dt = datetime.fromisoformat(ts)
                ts_h = dt.strftime("%d/%m %H:%M")
            except (TypeError, ValueError):
                ts_h = ts

            target = scan.get("target", "?")
            profile = scan.get("profile_id", "?")
            elapsed = scan.get("elapsed_sec", 0)
            hosts = scan.get("hosts", [])
            n_up = sum(1 for h in hosts if h.get("status") == "up")

            row = Adw.ExpanderRow()
            row.set_title(f"{ts_h} — {target}")
            row.set_subtitle(
                f"perfil: {profile} · {n_up} host{'s' if n_up != 1 else ''} up · {elapsed}s"
            )

            for h in hosts:
                if h.get("status") != "up":
                    continue
                addr = h.get("address", "?")
                hostname = h.get("hostname", "")
                ports_open = sum(1 for p in h.get("ports", []) if p.get("state") == "open")

                h_row = Adw.ActionRow(title=hostname or addr)
                if hostname:
                    h_row.set_subtitle(addr)
                h_row.add_css_class("property")
                if ports_open > 0:
                    pl = Gtk.Label(label=f"{ports_open} portas")
                    pl.add_css_class("monospace")
                    pl.add_css_class("caption")
                    pl.add_css_class("success")
                    h_row.add_suffix(pl)
                row.add_row(h_row)

            self._scans_group.add(row)
            self._scan_rows.append(row)

        return False
