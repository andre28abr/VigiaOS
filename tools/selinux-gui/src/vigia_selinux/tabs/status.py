"""Tab Status: modo runtime, modo persistente, info de policy."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .. import backend
from ._helpers import show_error


class StatusTab(Adw.PreferencesPage):
    def __init__(self) -> None:
        super().__init__()

        # ---- Banner para Disabled ----
        self._disabled_banner = Adw.Banner()
        self._disabled_banner.set_title(
            "⚠ SELinux esta DISABLED. Sistema sem protecao MAC. "
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
            "Valor em /etc/selinux/config — aplicado no proximo reboot"
        )
        self._persistent_value = Gtk.Label()
        self._persistent_value.add_css_class("dim-label")
        self._persistent_row.add_suffix(self._persistent_value)
        overview.add(self._persistent_row)

        self._policy_row = Adw.ActionRow()
        self._policy_row.set_title("Politica carregada")
        self._policy_value = Gtk.Label()
        self._policy_value.add_css_class("dim-label")
        self._policy_row.add_suffix(self._policy_value)
        overview.add(self._policy_row)

        self._version_row = Adw.ActionRow()
        self._version_row.set_title("Versao da politica")
        self._version_value = Gtk.Label()
        self._version_value.add_css_class("dim-label")
        self._version_row.add_suffix(self._version_value)
        overview.add(self._version_row)

        self.add(overview)

        # ---- Grupo acoes runtime ----
        runtime = Adw.PreferencesGroup()
        runtime.set_title("Acoes runtime")
        runtime.set_description("Mudam o estado atual. NAO persistem no reboot.")

        self._enforcing_row = Adw.ActionRow()
        self._enforcing_row.set_title("Modo Enforcing")
        self._enforcing_row.set_subtitle(
            "ON = SELinux bloqueia. OFF = permissive (so loga). "
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
        persistent.set_title("Modo persistente (/etc/selinux/config)")
        persistent.set_description(
            "Toma efeito no proximo boot. Disabled exige reboot para tomar efeito."
        )

        self._persistent_combo = Adw.ComboRow()
        self._persistent_combo.set_title("Modo no proximo boot")
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
        refresh_row = Adw.ActionRow()
        refresh_row.set_title("Recarregar estado")
        btn = Gtk.Button(label="Atualizar")
        btn.add_css_class("pill")
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked", lambda _b: self.refresh())
        refresh_row.add_suffix(btn)
        refresh.add(refresh_row)
        self.add(refresh)

        # Estado inicial
        self._suppress_combo = False
        self.refresh()

    def refresh(self) -> None:
        mode = backend.get_mode()
        policy = backend.get_policy_type()
        version = backend.get_policy_version()
        persistent = backend.get_persistent_mode()

        self._mode_value.set_text(mode)
        self._persistent_value.set_text(persistent)
        self._policy_value.set_text(policy)
        self._version_value.set_text(version)

        for css in ("error", "warning", "success"):
            self._mode_value.remove_css_class(css)
        if mode == "Enforcing":
            self._mode_value.add_css_class("success")
        elif mode == "Permissive":
            self._mode_value.add_css_class("warning")
        else:
            self._mode_value.add_css_class("error")

        # Switch sem disparar callback
        is_enforcing = mode == "Enforcing"
        self._enforcing_switch.set_active(is_enforcing)
        self._enforcing_switch.set_state(is_enforcing)
        self._enforcing_switch.set_sensitive(mode in ("Enforcing", "Permissive"))

        # Combo: ajusta para o modo persistente atual
        idx_map = {"enforcing": 0, "permissive": 1, "disabled": 2}
        idx = idx_map.get(persistent, 0)
        self._suppress_combo = True
        self._persistent_combo.set_selected(idx)
        self._suppress_combo = False

    def _on_enforcing_toggle(self, switch: Gtk.Switch, value: bool) -> bool:
        try:
            backend.set_mode_enforcing(value)
            switch.set_state(value)
        except Exception as e:
            switch.set_state(not value)
            show_error(self, "Falha ao mudar modo runtime", str(e))
        return True

    def _on_persistent_change(self, combo: Adw.ComboRow, _pspec: object) -> None:
        if self._suppress_combo:
            return
        model = combo.get_model()
        if model is None:
            return
        idx = combo.get_selected()
        mode = model.get_string(idx)
        try:
            backend.set_persistent_mode(mode)
            self.refresh()
        except Exception as e:
            show_error(self, "Falha ao editar /etc/selinux/config", str(e))
            self.refresh()
