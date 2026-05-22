"""Janela principal do Vigia SELinux GUI.

Layout: HeaderBar com ViewSwitcher entre duas paginas:
- Status: modo atual, policy, toggle Enforcing/Permissive
- Booleans: lista pesquisavel de SELinux booleans com switches
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from . import backend


class VigiaSelinuxWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("SELinux Manager")
        self.set_default_size(820, 620)

        toolbar = Adw.ToolbarView()

        # View stack com paginas + switcher no header
        self.view_stack = Adw.ViewStack()
        self.view_stack.add_titled_with_icon(
            self._build_status_page(), "status", "Status", "dialog-information-symbolic"
        )
        self.view_stack.add_titled_with_icon(
            self._build_booleans_page(), "booleans", "Booleans", "preferences-system-symbolic"
        )

        header = Adw.HeaderBar()
        switcher = Adw.ViewSwitcher()
        switcher.set_stack(self.view_stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        header.set_title_widget(switcher)

        toolbar.add_top_bar(header)
        toolbar.set_content(self.view_stack)
        self.set_content(toolbar)

    # ========================================================================
    # Status page
    # ========================================================================

    def _build_status_page(self) -> Gtk.Widget:
        page = Adw.PreferencesPage()

        # Grupo 1: visao geral
        overview = Adw.PreferencesGroup()
        overview.set_title("Estado atual do SELinux")

        self._mode_row = Adw.ActionRow()
        self._mode_row.set_title("Modo")
        self._mode_value = Gtk.Label()
        self._mode_value.add_css_class("title-4")
        self._mode_row.add_suffix(self._mode_value)
        overview.add(self._mode_row)

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

        page.add(overview)

        # Grupo 2: toggle de modo
        actions = Adw.PreferencesGroup()
        actions.set_title("Acoes")
        actions.set_description(
            "Muda modo em tempo de execucao. Para persistir no boot, edite "
            "/etc/selinux/config + reboot."
        )

        self._enforcing_row = Adw.ActionRow()
        self._enforcing_row.set_title("Modo Enforcing")
        self._enforcing_row.set_subtitle(
            "ON = SELinux bloqueia operacoes nao autorizadas. "
            "OFF = SELinux apenas registra (permissive)."
        )
        self._enforcing_switch = Gtk.Switch()
        self._enforcing_switch.set_valign(Gtk.Align.CENTER)
        self._enforcing_switch.connect("state-set", self._on_enforcing_toggle)
        self._enforcing_row.add_suffix(self._enforcing_switch)
        self._enforcing_row.set_activatable_widget(self._enforcing_switch)
        actions.add(self._enforcing_row)

        refresh_row = Adw.ActionRow()
        refresh_row.set_title("Recarregar status")
        refresh_btn = Gtk.Button(label="Atualizar")
        refresh_btn.add_css_class("pill")
        refresh_btn.set_valign(Gtk.Align.CENTER)
        refresh_btn.connect("clicked", lambda _b: self._refresh_status())
        refresh_row.add_suffix(refresh_btn)
        actions.add(refresh_row)

        page.add(actions)

        # Preenche valores iniciais
        self._refresh_status()

        return page

    def _refresh_status(self) -> None:
        mode = backend.get_mode()
        policy = backend.get_policy_type()
        version = backend.get_policy_version()

        self._mode_value.set_text(mode)
        self._policy_value.set_text(policy)
        self._version_value.set_text(version)

        # Color do modo conforme estado
        for css in ("error", "warning", "success"):
            self._mode_value.remove_css_class(css)
        if mode == "Enforcing":
            self._mode_value.add_css_class("success")
        elif mode == "Permissive":
            self._mode_value.add_css_class("warning")
        else:
            self._mode_value.add_css_class("error")

        # Atualiza switch sem disparar callback
        is_enforcing = mode == "Enforcing"
        with _block_signal(self._enforcing_switch, "state-set"):
            self._enforcing_switch.set_active(is_enforcing)
            self._enforcing_switch.set_state(is_enforcing)
        # Desabilita switch se SELinux esta disabled
        self._enforcing_switch.set_sensitive(mode in ("Enforcing", "Permissive"))

    def _on_enforcing_toggle(self, switch: Gtk.Switch, value: bool) -> bool:
        try:
            backend.set_mode_enforcing(value)
            switch.set_state(value)
        except Exception as e:
            switch.set_state(not value)
            self._show_error("Falha ao mudar modo SELinux", str(e))
        return True

    # ========================================================================
    # Booleans page
    # ========================================================================

    def _build_booleans_page(self) -> Gtk.Widget:
        # Estrutura: ScrolledWindow com search no topo + ListBox de switches
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        # Search bar
        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text(
            "Filtrar booleans (ex: ssh, httpd, samba, ...)"
        )
        self._search_entry.connect("search-changed", self._on_search_changed)
        box.append(self._search_entry)

        # Lista
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._booleans_list = Gtk.ListBox()
        self._booleans_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._booleans_list.add_css_class("boxed-list")
        self._booleans_list.set_filter_func(self._filter_booleans)

        scrolled.set_child(self._booleans_list)
        box.append(scrolled)

        # Botao de refresh embaixo
        refresh_btn = Gtk.Button(label="Recarregar lista")
        refresh_btn.set_halign(Gtk.Align.END)
        refresh_btn.connect("clicked", lambda _b: self._refresh_booleans())
        box.append(refresh_btn)

        self._refresh_booleans()
        return box

    def _refresh_booleans(self) -> None:
        # Limpa lista
        while child := self._booleans_list.get_first_child():
            self._booleans_list.remove(child)

        booleans = backend.list_booleans()
        if not booleans:
            empty = Adw.ActionRow()
            empty.set_title("Nenhum boolean encontrado")
            empty.set_subtitle("SELinux pode nao estar instalado ou nao ha policy carregada.")
            self._booleans_list.append(empty)
            return

        for b in sorted(booleans, key=lambda x: x.name):
            row = Adw.ActionRow()
            row.set_title(b.name)
            row.set_subtitle("")

            switch = Gtk.Switch()
            switch.set_valign(Gtk.Align.CENTER)
            switch.set_active(b.value)
            # Captura o nome via closure no connect
            switch.connect(
                "state-set",
                lambda sw, val, name=b.name: self._on_boolean_toggle(sw, val, name),
            )
            row.add_suffix(switch)
            row.set_activatable_widget(switch)

            self._booleans_list.append(row)

    def _filter_booleans(self, row: Gtk.ListBoxRow) -> bool:
        query = self._search_entry.get_text().lower().strip()
        if not query:
            return True
        if not isinstance(row, Adw.ActionRow):
            return True
        return query in row.get_title().lower()

    def _on_search_changed(self, _entry: Gtk.SearchEntry) -> None:
        self._booleans_list.invalidate_filter()

    def _on_boolean_toggle(self, switch: Gtk.Switch, value: bool, name: str) -> bool:
        try:
            backend.set_boolean(name, value, persistent=True)
            switch.set_state(value)
        except Exception as e:
            switch.set_state(not value)
            self._show_error(f"Falha ao mudar boolean '{name}'", str(e))
        return True

    # ========================================================================
    # Helpers
    # ========================================================================

    def _show_error(self, heading: str, message: str) -> None:
        dlg = Adw.AlertDialog(heading=heading, body=message)
        dlg.add_response("ok", "OK")
        dlg.present(self)


class _block_signal:
    """Context manager que bloqueia temporariamente um signal handler."""

    def __init__(self, widget, signal_name: str):
        self.widget = widget
        self.signal_name = signal_name
        self.handler_id = None

    def __enter__(self):
        # Acha o ultimo handler conectado para esse signal
        # (simplificacao: bloqueia handlers do tipo 'state-set' usando GObject.signal_handlers_block_by_func nao funciona aqui)
        # Para nosso uso (set programatico do switch sem trigger), usamos set_state que NAO emite state-set.
        # Entao este context manager e' mais um placeholder; o trabalho real e' usar set_state em vez de set_active.
        return self

    def __exit__(self, *args):
        return False
