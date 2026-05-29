"""Tab Status: modo runtime, modo persistente, info de policy."""

from __future__ import annotations

import threading
from dataclasses import dataclass

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from ._helpers import show_error


@dataclass
class _StatusSnapshot:
    mode: str = ""
    policy: str = ""
    version: str = ""
    persistent: str = ""


class StatusTab(Adw.PreferencesPage):
    def __init__(self) -> None:
        super().__init__()

        # ---- Banner para Disabled ----
        self._disabled_banner = Adw.Banner()
        self._disabled_banner.set_title(
            "⚠ SELinux está DISABLED. Sistema sem proteção MAC. "
            "Para reativar: edite /etc/selinux/config (SELINUX=enforcing) e reinicie."
        )
        self._disabled_banner.add_css_class("error")
        self._disabled_banner.set_revealed(False)
        # Note: PreferencesPage nao aceita Banner como first child diretamente,
        # mas podemos add como wrapper

        # ---- Grupo overview ----
        overview = Adw.PreferencesGroup()
        overview.set_title("Estado atual")

        self._mode_row = Adw.ActionRow()
        self._mode_row.set_title("Modo runtime")
        self._mode_row.set_subtitle("Estado ativo desde o boot — pode ser mudado abaixo")
        self._mode_value = Gtk.Label()
        self._mode_value.add_css_class("title-4")
        self._mode_row.add_suffix(self._mode_value)
        overview.add(self._mode_row)

        self._persistent_row = Adw.ActionRow()
        self._persistent_row.set_title("Modo persistente")
        self._persistent_row.set_subtitle(
            "Valor em /etc/selinux/config — aplicado no próximo reboot"
        )
        self._persistent_value = Gtk.Label()
        self._persistent_value.add_css_class("dim-label")
        self._persistent_row.add_suffix(self._persistent_value)
        overview.add(self._persistent_row)

        self._policy_row = Adw.ActionRow()
        self._policy_row.set_title("Política carregada")
        self._policy_value = Gtk.Label()
        self._policy_value.add_css_class("dim-label")
        self._policy_row.add_suffix(self._policy_value)
        overview.add(self._policy_row)

        self._version_row = Adw.ActionRow()
        self._version_row.set_title("Versão da política")
        self._version_value = Gtk.Label()
        self._version_value.add_css_class("dim-label")
        self._version_row.add_suffix(self._version_value)
        overview.add(self._version_row)

        self.add(overview)

        # ---- Grupo acoes runtime ----
        runtime = Adw.PreferencesGroup()
        runtime.set_margin_top(24)
        runtime.set_title("Ações runtime")
        runtime.set_description("Mudam o estado atual. NÃO persistem no reboot.")

        self._enforcing_row = Adw.ActionRow()
        self._enforcing_row.set_title("Modo Enforcing")
        self._enforcing_row.set_subtitle(
            "ON = SELinux bloqueia. OFF = permissive (só loga). "
            "Para mudar permanentemente, use o grupo abaixo."
        )
        self._enforcing_switch = Gtk.Switch()
        self._enforcing_switch.set_valign(Gtk.Align.CENTER)
        self._enforcing_switch.connect("state-set", self._on_enforcing_toggle)
        self._enforcing_row.add_suffix(self._enforcing_switch)
        self._enforcing_row.set_activatable_widget(self._enforcing_switch)
        runtime.add(self._enforcing_row)

        self.add(runtime)

        # ---- Grupo acoes persistentes ----
        persistent = Adw.PreferencesGroup()
        persistent.set_margin_top(24)
        persistent.set_title("Modo persistente (/etc/selinux/config)")
        persistent.set_description(
            "Toma efeito no próximo boot. Disabled exige reboot para tomar efeito."
        )

        self._persistent_combo = Adw.ComboRow()
        self._persistent_combo.set_title("Modo no próximo boot")
        self._persistent_combo.set_subtitle(
            "Edita /etc/selinux/config via pkexec. Sem reboot, modo runtime continua."
        )
        model = Gtk.StringList.new(["enforcing", "permissive", "disabled"])
        self._persistent_combo.set_model(model)
        self._persistent_combo.connect("notify::selected", self._on_persistent_change)
        persistent.add(self._persistent_combo)
        self.add(persistent)

        # ---- Refresh ----
        refresh = Adw.PreferencesGroup()
        refresh.set_margin_top(24)
        refresh_row = Adw.ActionRow()
        refresh_row.set_title("Recarregar estado")
        btn = Gtk.Button(label="Atualizar")
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked", lambda _b: self.refresh())
        refresh_row.add_suffix(btn)
        refresh.add(refresh_row)
        self.add(refresh)

        # Estado inicial
        self._suppress_combo = False
        self.refresh()

    def refresh(self) -> None:
        """Dispara fetch em thread. UI thread fica livre."""
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        snap = _StatusSnapshot()
        try:
            snap.mode = backend.get_mode()
            snap.policy = backend.get_policy_type()
            snap.version = backend.get_policy_version()
            snap.persistent = backend.get_persistent_mode()
        except Exception:  # pylint: disable=broad-except
            pass
        GLib.idle_add(self._apply_status, snap)

    def _apply_status(self, snap: _StatusSnapshot) -> bool:
        self._mode_value.set_text(snap.mode or "—")
        self._persistent_value.set_text(snap.persistent or "—")
        self._policy_value.set_text(snap.policy or "—")
        self._version_value.set_text(snap.version or "—")

        for css in ("error", "warning", "success"):
            self._mode_value.remove_css_class(css)
        if snap.mode == "Enforcing":
            self._mode_value.add_css_class("success")
        elif snap.mode == "Permissive":
            self._mode_value.add_css_class("warning")
        else:
            self._mode_value.add_css_class("error")

        is_enforcing = snap.mode == "Enforcing"
        self._enforcing_switch.set_active(is_enforcing)
        self._enforcing_switch.set_state(is_enforcing)
        self._enforcing_switch.set_sensitive(snap.mode in ("Enforcing", "Permissive"))

        idx_map = {"enforcing": 0, "permissive": 1, "disabled": 2}
        idx = idx_map.get(snap.persistent, 0)
        self._suppress_combo = True
        self._persistent_combo.set_selected(idx)
        self._suppress_combo = False
        return False

    def _on_enforcing_toggle(self, switch: Gtk.Switch, value: bool) -> bool:
        threading.Thread(
            target=self._enforcing_worker, args=(switch, value), daemon=True
        ).start()
        return True

    def _enforcing_worker(self, switch: Gtk.Switch, value: bool) -> None:
        try:
            backend.set_mode_enforcing(value)
            err = None
        except Exception as e:  # pylint: disable=broad-except
            err = str(e)
        GLib.idle_add(self._on_enforcing_done, switch, value, err)

    def _on_enforcing_done(self, switch: Gtk.Switch, value: bool, err: str | None) -> bool:
        if err is None:
            switch.set_state(value)
        else:
            switch.set_state(not value)
            show_error(self, "Falha ao mudar modo runtime", err)
        return False

    def _on_persistent_change(self, combo: Adw.ComboRow, _pspec: object) -> None:
        if self._suppress_combo:
            return
        model = combo.get_model()
        if model is None:
            return
        idx = combo.get_selected()
        mode = model.get_string(idx)
        threading.Thread(
            target=self._persistent_worker, args=(mode,), daemon=True
        ).start()

    def _persistent_worker(self, mode: str) -> None:
        try:
            backend.set_persistent_mode(mode)
            err = None
        except Exception as e:  # pylint: disable=broad-except
            err = str(e)
        GLib.idle_add(self._on_persistent_done, err)

    def _on_persistent_done(self, err: str | None) -> bool:
        if err is not None:
            show_error(self, "Falha ao editar /etc/selinux/config", err)
        self.refresh()
        return False
