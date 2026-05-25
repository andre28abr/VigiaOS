"""Tab Status: estado do daemon firewalld + zona default + active zones."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from ._helpers import show_error


@dataclass
class _StatusSnapshot:
    running: bool = False
    available: bool = False
    zones: list = field(default_factory=list)
    default_zone: str = ""
    active_zones: list = field(default_factory=list)


class StatusTab(Adw.PreferencesPage):
    def __init__(self) -> None:
        super().__init__()

        # ============= Grupo daemon ============= #
        daemon = Adw.PreferencesGroup()
        daemon.set_title("Estado do firewalld")

        self._running_row = Adw.ActionRow()
        self._running_row.set_title("Daemon")
        self._running_label = Gtk.Label()
        self._running_label.add_css_class("title-4")
        self._running_row.add_suffix(self._running_label)
        daemon.add(self._running_row)

        # Botoes Start / Stop (mostrados conforme estado)
        self._toggle_row = Adw.ActionRow()
        self._toggle_row.set_title("Acao")
        self._toggle_row.set_subtitle(
            "Liga/desliga o firewalld. Use Privacy Controls -> Rede para"
            " controlar 'habilitar no boot' (enable/disable)."
        )
        self._toggle_btn = Gtk.Button()
        self._toggle_btn.set_valign(Gtk.Align.CENTER)
        self._toggle_btn.add_css_class("pill")
        self._toggle_btn.connect("clicked", self._on_toggle)
        self._toggle_row.add_suffix(self._toggle_btn)
        daemon.add(self._toggle_row)

        self.add(daemon)

        # ============= Grupo zona default ============= #
        zonegrp = Adw.PreferencesGroup()
        zonegrp.set_title("Zona padrao")
        zonegrp.set_description(
            "Zona aplicada a interfaces que nao tem zona explicita."
            " Define o nivel de protecao default."
        )

        self._default_zone_combo = Adw.ComboRow()
        self._default_zone_combo.set_title("Zona padrao")
        self._default_zone_combo.set_subtitle(
            "Mais comuns: public (estrito, default Fedora), home (relaxado), "
            "internal (mais relaxado), trusted (sem firewall na pratica), drop (bloqueia tudo)."
        )
        self._zone_model = Gtk.StringList()
        self._default_zone_combo.set_model(self._zone_model)
        self._suppress_combo = False
        self._default_zone_combo.connect("notify::selected", self._on_default_change)
        zonegrp.add(self._default_zone_combo)

        self.add(zonegrp)

        # ============= Grupo active zones ============= #
        active = Adw.PreferencesGroup()
        active.set_title("Zonas ativas")
        active.set_description(
            "Quais zonas estao em uso por quais interfaces/sources."
        )
        self._active_group = active
        self._active_rows: list[Adw.ActionRow] = []
        self.add(active)

        # ============= Refresh ============= #
        refresh = Adw.PreferencesGroup()
        refresh_row = Adw.ActionRow()
        refresh_row.set_title("Recarregar estado")
        btn = Gtk.Button(label="Atualizar")
        btn.add_css_class("pill")
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked", lambda _b: self.refresh())
        refresh_row.add_suffix(btn)
        refresh.add(refresh_row)
        self.add(refresh)

        self.refresh()

    def refresh(self) -> None:
        """Dispara coleta em thread (6+ subprocess firewall-cmd) sem bloquear UI."""
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        snap = _StatusSnapshot()
        try:
            snap.running = backend.is_running()
            snap.available = backend.is_firewalld_available()
            snap.zones = backend.list_zones()
            snap.default_zone = backend.get_default_zone()
            snap.active_zones = backend.get_active_zones()
        except Exception:  # pylint: disable=broad-except
            pass
        GLib.idle_add(self._apply_status, snap)

    def _apply_status(self, snap: _StatusSnapshot) -> bool:
        # Daemon label
        self._running_label.set_text("running" if snap.running else "stopped")
        for css in ("success", "error"):
            self._running_label.remove_css_class(css)
        self._running_label.add_css_class("success" if snap.running else "error")

        # Toggle btn
        self._toggle_btn.set_label("Stop" if snap.running else "Start")
        for css in ("destructive-action", "suggested-action"):
            self._toggle_btn.remove_css_class(css)
        self._toggle_btn.add_css_class("destructive-action" if snap.running else "suggested-action")
        self._toggle_btn.set_sensitive(snap.available)

        # Default zone combo
        self._suppress_combo = True
        while self._zone_model.get_n_items() > 0:
            self._zone_model.remove(0)
        idx_to_select = 0
        for i, zname in enumerate(snap.zones):
            self._zone_model.append(zname)
            if zname == snap.default_zone:
                idx_to_select = i
        self._default_zone_combo.set_selected(idx_to_select)
        self._suppress_combo = False

        # Active zones
        for r in self._active_rows:
            self._active_group.remove(r)
        self._active_rows.clear()
        for az in snap.active_zones:
            row = Adw.ActionRow()
            row.set_title(az.name)
            parts: list[str] = []
            if az.interfaces:
                parts.append("interfaces: " + ", ".join(az.interfaces))
            if az.sources:
                parts.append("sources: " + ", ".join(az.sources))
            row.set_subtitle(" • ".join(parts) if parts else "(sem detalhes)")
            self._active_group.add(row)
            self._active_rows.append(row)
        if not self._active_rows:
            row = Adw.ActionRow()
            row.set_title("Nenhuma zona ativa")
            row.set_subtitle("firewalld parado, ou sem interfaces configuradas.")
            self._active_group.add(row)
            self._active_rows.append(row)
        return False

    def _on_toggle(self, button: Gtk.Button) -> None:
        # start/stop firewalld via pkexec — pode demorar
        threading.Thread(target=self._toggle_worker, daemon=True).start()

    def _toggle_worker(self) -> None:
        try:
            if backend.is_running():
                backend.stop_firewalld()
            else:
                backend.start_firewalld()
            err = None
        except Exception as e:  # pylint: disable=broad-except
            err = str(e)
        GLib.idle_add(self._on_toggle_done, err)

    def _on_toggle_done(self, err: str | None) -> bool:
        if err is not None:
            show_error(self, "Falha ao mudar estado do firewalld", err)
        self.refresh()
        return False

    def _on_default_change(self, combo: Adw.ComboRow, _pspec: object) -> None:
        if self._suppress_combo:
            return
        idx = combo.get_selected()
        if idx >= self._zone_model.get_n_items():
            return
        new_zone = self._zone_model.get_string(idx)
        # set_default_zone faz pkexec — vai pra thread
        threading.Thread(
            target=self._default_zone_worker, args=(new_zone,), daemon=True
        ).start()

    def _default_zone_worker(self, new_zone: str) -> None:
        try:
            backend.set_default_zone(new_zone)
            err = None
        except Exception as e:  # pylint: disable=broad-except
            err = str(e)
        GLib.idle_add(self._on_default_zone_done, err)

    def _on_default_zone_done(self, err: str | None) -> bool:
        if err is not None:
            show_error(self, "Falha ao mudar zona padrao", err)
        self.refresh()
        return False
