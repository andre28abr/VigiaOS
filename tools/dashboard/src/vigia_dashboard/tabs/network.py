"""Tab Rede: banda por processo (nethogs) — quem está usando a rede.

Medição pontual (snapshot ~4s) via pkexec. Construída lazy (só quando o
user visita a aba), então o nethogs só roda no clique do botão.
"""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import net_bandwidth as backend
from ._helpers import make_clamp


class NetworkTab(Adw.Bin):
    """Mede banda por processo via nethogs (snapshot via pkexec)."""

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._rows: list = []

        header_lbl = Gtk.Label(label="Banda por processo")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(8)

        header_desc = Gtk.Label(
            label=(
                "Mede <b>quanto de rede cada processo está usando agora</b> "
                "(↑ enviado · ↓ recebido). Útil pra achar quem está "
                "consumindo banda ou <b>suspeitar de exfiltração</b> — um "
                "processo mandando dados pra fora sem motivo.\n\n"
                "É uma <b>medição pontual</b> (~4s) via <tt>nethogs</tt>. "
                "Pede senha de administrador (o kernel só deixa ver tráfego "
                "por processo com privilégio). <i>Read-only</i>: só observa."
            )
        )
        header_desc.set_use_markup(True)
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(24)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.START)
        self._spinner = Gtk.Spinner()
        btn_box.append(self._spinner)
        self._measure_btn = Gtk.Button(label="Medir banda (~4s)")
        self._measure_btn.add_css_class("suggested-action")
        self._measure_btn.connect("clicked", lambda _b: self._start())
        btn_box.append(self._measure_btn)

        self._status = Gtk.Label(label="")
        self._status.add_css_class("dim-label")
        self._status.set_halign(Gtk.Align.START)
        self._status.set_wrap(True)
        self._status.set_xalign(0)
        self._status.set_margin_top(12)
        self._status.set_margin_bottom(4)

        self._group = Adw.PreferencesGroup()
        self._group.set_margin_top(20)
        self._group.set_title("Processos (por tráfego)")

        if not backend.nethogs_installed():
            self._measure_btn.set_sensitive(False)
            self._status.set_label(
                "nethogs não instalado. Instale pelo Instalador "
                "(categoria Monitoramento) pra medir banda por processo."
            )

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(24)
        outer.set_margin_bottom(32)
        outer.set_margin_start(28)
        outer.set_margin_end(28)
        outer.append(header_lbl)
        outer.append(header_desc)
        outer.append(btn_box)
        outer.append(self._status)
        outer.append(self._group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

    def _start(self) -> None:
        if self._running:
            return
        self._running = True
        self._measure_btn.set_sensitive(False)
        self._spinner.start()
        self._status.set_label("Medindo... (pede senha de administrador)")
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self) -> None:
        result = backend.bandwidth_snapshot_blocking()
        GLib.idle_add(self._on_done, result)

    def _on_done(self, result: backend.BandwidthResult) -> bool:
        self._running = False
        self._measure_btn.set_sensitive(True)
        self._spinner.stop()

        for r in self._rows:
            self._group.remove(r)
        self._rows = []

        if result.error:
            self._status.set_label(result.error)
            return False

        self._status.set_label(
            f"{len(result.rows)} processo(s) com tráfego no período."
        )
        for pb in result.rows[:40]:
            row = Adw.ActionRow(title=pb.program or "?")
            row.set_subtitle(f"PID {pb.pid}")
            rate = Gtk.Label(
                label=f"↑ {pb.sent_kbps:.1f}   ↓ {pb.recv_kbps:.1f} KB/s"
            )
            rate.add_css_class("monospace")
            rate.add_css_class("caption")
            rate.set_valign(Gtk.Align.CENTER)
            row.add_suffix(rate)
            self._group.add(row)
            self._rows.append(row)
        return False
