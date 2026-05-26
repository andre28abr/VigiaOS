"""Tab Visao Geral: hero + KPIs do scan."""

from __future__ import annotations

import threading
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from ..capabilities import risk_for_cap
from ._helpers import make_clamp, show_error


class OverviewTab(Adw.Bin):
    """Hero card com contagem + acao de scan."""

    def __init__(self, on_scan_done: Callable[[list], None]) -> None:
        super().__init__()
        self._on_scan_done = on_scan_done
        self._running = False
        self._pulse_id: int | None = None
        self._has_data = False

        # Hero
        self._hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._hero.set_halign(Gtk.Align.CENTER)
        self._hero.set_margin_top(32)
        self._hero.set_margin_bottom(20)

        self._state_label = Gtk.Label(label="—")
        self._state_label.add_css_class("title-1")
        self._state_label.set_halign(Gtk.Align.CENTER)
        self._state_label.add_css_class("dim-label")

        self._state_sub = Gtk.Label(label="Nenhum scan feito ainda")
        self._state_sub.add_css_class("title-4")
        self._state_sub.add_css_class("dim-label")
        self._state_sub.set_halign(Gtk.Align.CENTER)
        self._state_sub.set_wrap(True)
        self._state_sub.set_justify(Gtk.Justification.CENTER)
        self._state_sub.set_max_width_chars(56)

        self._hero.append(self._state_label)
        self._hero.append(self._state_sub)

        # KPIs
        self._stats_group = Adw.PreferencesGroup()
        self._stats_group.set_title("Ultimo scan")

        self._row_total = Adw.ActionRow(title="Binarios com capabilities")
        self._row_total.add_css_class("property")
        self._lbl_total = Gtk.Label(label="—")
        self._lbl_total.add_css_class("monospace")
        self._row_total.add_suffix(self._lbl_total)
        self._stats_group.add(self._row_total)

        self._row_alto = Adw.ActionRow(title="Risco ALTO")
        self._row_alto.set_subtitle("ex: cap_sys_admin, cap_setuid, cap_dac_override")
        self._row_alto.add_css_class("property")
        self._lbl_alto = Gtk.Label(label="—")
        self._lbl_alto.add_css_class("monospace")
        self._row_alto.add_suffix(self._lbl_alto)
        self._stats_group.add(self._row_alto)

        self._row_medio = Adw.ActionRow(title="Risco MEDIO")
        self._row_medio.set_subtitle("ex: cap_net_admin, cap_chown, cap_kill")
        self._row_medio.add_css_class("property")
        self._lbl_medio = Gtk.Label(label="—")
        self._lbl_medio.add_css_class("monospace")
        self._row_medio.add_suffix(self._lbl_medio)
        self._stats_group.add(self._row_medio)

        self._row_baixo = Adw.ActionRow(title="Risco BAIXO")
        self._row_baixo.set_subtitle("ex: cap_net_bind_service, cap_audit_write")
        self._row_baixo.add_css_class("property")
        self._lbl_baixo = Gtk.Label(label="—")
        self._lbl_baixo.add_css_class("monospace")
        self._row_baixo.add_suffix(self._lbl_baixo)
        self._stats_group.add(self._row_baixo)

        # Action group
        self._action_group = Adw.PreferencesGroup()
        self._action_group.set_margin_top(24)
        self._action_group.set_title("Scan")
        self._action_group.set_description(
            "Lista todos os binarios em /usr, /opt, /var, /srv com capabilities setadas. "
            "Roda `getcap -r` via pkexec (1 dialog) — leva 5-30 segundos."
        )

        scan_row = Adw.ActionRow(title="Escanear sistema")
        scan_row.set_subtitle("Cobertura total via pkexec")
        self._scan_btn = Gtk.Button(label="Escanear")
        self._scan_btn.add_css_class("suggested-action")
        self._scan_btn.set_valign(Gtk.Align.CENTER)
        self._scan_btn.connect("clicked", self._on_scan_clicked)
        scan_row.add_suffix(self._scan_btn)
        self._action_group.add(scan_row)

        scan_user_row = Adw.ActionRow(title="Escanear (sem admin)")
        scan_user_row.set_subtitle("So paths do user — cobertura parcial, sem pkexec")
        self._scan_user_btn = Gtk.Button(label="Quick scan")
        self._scan_user_btn.set_valign(Gtk.Align.CENTER)
        self._scan_user_btn.connect("clicked", self._on_quick_scan_clicked)
        scan_user_row.add_suffix(self._scan_user_btn)
        self._action_group.add(scan_user_row)

        # Progress
        self._progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._progress_box.set_visible(False)
        self._progress_box.set_margin_top(8)
        self._progress_label = Gtk.Label(label="Escaneando...")
        self._progress_label.add_css_class("dim-label")
        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.set_pulse_step(0.1)
        self._progress_box.append(self._progress_label)
        self._progress_box.append(self._progress_bar)

        # Layout
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        outer.set_margin_top(0)
        outer.set_margin_bottom(28)
        outer.set_margin_start(20)
        outer.set_margin_end(20)
        outer.append(self._hero)
        outer.append(self._stats_group)
        outer.append(self._action_group)
        outer.append(self._progress_box)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

    # ============================================================
    # Refresh com resultado do scan
    # ============================================================

    def refresh(self, binaries: list[backend.BinaryWithCaps]) -> None:
        self._has_data = True

        total = len(binaries)
        risk_counts = {"alto": 0, "medio": 0, "baixo": 0, "desconhecida": 0}
        for b in binaries:
            for cap_name in b.cap_names:
                r = risk_for_cap(cap_name)
                risk_counts[r] = risk_counts.get(r, 0) + 1
                # Conta uma vez por capability — pode contar mais que num binarios
                # se um binario tem multiplas caps. Aceitavel.

        # Hero
        for cls in ("success", "warning", "error", "dim-label"):
            self._state_label.remove_css_class(cls)

        if total == 0:
            self._state_label.set_label("0")
            self._state_label.add_css_class("success")
            self._state_sub.set_label(
                "Nenhum binario com capabilities. Sistema limpo."
            )
        elif risk_counts["alto"] > 0:
            self._state_label.set_label(str(risk_counts["alto"]))
            self._state_label.add_css_class("error")
            self._state_sub.set_label(
                f"{risk_counts['alto']} capabilities de risco ALTO encontradas. "
                "Veja a aba 'Binarios' filtrando por 'alto'."
            )
        elif risk_counts["medio"] > 0:
            self._state_label.set_label(str(total))
            self._state_label.add_css_class("warning")
            self._state_sub.set_label(
                f"{total} binarios com capabilities. Nenhuma de risco ALTO."
            )
        else:
            self._state_label.set_label(str(total))
            self._state_label.add_css_class("success")
            self._state_sub.set_label(
                f"{total} binarios com capabilities, todas de risco baixo."
            )

        # Stats
        self._lbl_total.set_label(str(total))
        self._lbl_alto.set_label(str(risk_counts["alto"]))
        self._lbl_medio.set_label(str(risk_counts["medio"]))
        self._lbl_baixo.set_label(str(risk_counts["baixo"]))

        # Color do KPI alto
        for cls in ("error", "warning", "success", "dim-label"):
            self._lbl_alto.remove_css_class(cls)
        if risk_counts["alto"] > 0:
            self._lbl_alto.add_css_class("error")
        else:
            self._lbl_alto.add_css_class("dim-label")

    # ============================================================
    # Scan actions
    # ============================================================

    def _on_scan_clicked(self, _btn: Gtk.Button) -> None:
        if self._running:
            return
        self._set_running(True, "Escaneando todo o sistema (pode levar minutos)...")
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self) -> None:
        try:
            binaries, err = backend.scan_binaries_elevated()
        except Exception as e:  # pylint: disable=broad-except
            binaries, err = [], f"Excecao: {e}"
        GLib.idle_add(self._on_scan_done_cb, binaries, err)

    def _on_quick_scan_clicked(self, _btn: Gtk.Button) -> None:
        if self._running:
            return
        self._set_running(True, "Quick scan em paths comuns...")
        threading.Thread(target=self._quick_scan_worker, daemon=True).start()

    def _quick_scan_worker(self) -> None:
        try:
            binaries = backend.scan_binaries_user()
            err = ""
        except Exception as e:  # pylint: disable=broad-except
            binaries, err = [], f"Excecao: {e}"
        GLib.idle_add(self._on_scan_done_cb, binaries, err)

    def _on_scan_done_cb(self, binaries: list, err: str) -> bool:
        self._set_running(False)
        if err:
            show_error(self, "Scan falhou", err)
            return False
        self.refresh(binaries)
        self._on_scan_done(binaries)
        return False

    # ============================================================
    # Progress
    # ============================================================

    def _set_running(self, running: bool, label: str = "Trabalhando...") -> None:
        self._running = running
        self._scan_btn.set_sensitive(not running)
        self._scan_btn.set_label("Escaneando..." if running else "Escanear")
        self._scan_user_btn.set_sensitive(not running)
        self._progress_box.set_visible(running)
        self._progress_label.set_label(label)
        if running:
            if self._pulse_id is None:
                self._pulse_id = GLib.timeout_add(100, self._pulse_tick)
        else:
            if self._pulse_id is not None:
                GLib.source_remove(self._pulse_id)
                self._pulse_id = None

    def _pulse_tick(self) -> bool:
        self._progress_bar.pulse()
        return self._running
