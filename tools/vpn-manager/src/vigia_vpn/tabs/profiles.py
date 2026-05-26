"""Tab Perfis: lista perfis WireGuard em /etc/wireguard/ + connect/disconnect/import."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from ._helpers import make_clamp, show_error, show_info


class ProfilesTab(Adw.Bin):
    """Lista perfis WireGuard, conecta/desconecta, importa novos."""

    def __init__(self) -> None:
        super().__init__()
        self._profile_rows: list = []
        self._profiles: list = []
        self._active_ifaces: set[str] = set()
        self._running = False

        # Header
        header_lbl = Gtk.Label(label="Perfis WireGuard")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(8)

        header_desc = Gtk.Label(
            label=(
                "Configs em /etc/wireguard/*.conf. Listar e operar requer "
                "permissao admin (polkit). Clique 'Carregar perfis' para "
                "comecar."
            )
        )
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(24)

        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toolbar.set_margin_bottom(16)

        self._load_btn = Gtk.Button(label="Carregar perfis")
        self._load_btn.add_css_class("suggested-action")
        self._load_btn.connect("clicked", lambda _b: self._load_profiles())
        toolbar.append(self._load_btn)

        self._import_btn = Gtk.Button(label="Importar novo")
        self._import_btn.connect("clicked", lambda _b: self._show_import_dialog())
        toolbar.append(self._import_btn)

        # Profiles group
        self._profiles_group = Adw.PreferencesGroup()
        self._profiles_group.set_title("Perfis disponiveis")

        # Status pequeno / progress
        self._status_label = Gtk.Label(label="Nenhum perfil carregado.")
        self._status_label.add_css_class("dim-label")
        self._status_label.set_halign(Gtk.Align.START)
        self._status_label.set_margin_top(8)
        self._status_label.set_margin_bottom(8)

        # Layout
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(24)
        outer.set_margin_bottom(32)
        outer.set_margin_start(28)
        outer.set_margin_end(28)
        outer.append(header_lbl)
        outer.append(header_desc)
        outer.append(toolbar)
        outer.append(self._profiles_group)
        outer.append(self._status_label)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

    # ============================================================
    # Load profiles (via pkexec)
    # ============================================================

    def _load_profiles(self) -> None:
        if self._running:
            return
        self._set_running(True, "Carregando perfis...")
        threading.Thread(target=self._load_worker, daemon=True).start()

    def _load_worker(self) -> None:
        try:
            profiles, err = backend.list_profiles_elevated()
            active = set(backend.list_active_interfaces())
        except Exception as e:  # pylint: disable=broad-except
            profiles, err = [], f"Excecao: {e}"
            active = set()
        GLib.idle_add(self._on_load_done, profiles, active, err)

    def _on_load_done(self, profiles, active: set, err: str) -> bool:
        self._set_running(False)
        if err:
            show_error(self, "Falha ao carregar perfis", err)
            return False

        self._profiles = profiles
        self._active_ifaces = active
        self._render_profiles()
        return False

    def _render_profiles(self) -> None:
        # Clear
        for r in self._profile_rows:
            self._profiles_group.remove(r)
        self._profile_rows = []

        if not self._profiles:
            row = Adw.ActionRow(title="Nenhum perfil em /etc/wireguard/")
            row.set_subtitle(
                "Use 'Importar novo' acima ou copie um .conf via terminal "
                "(sudo cp meu.conf /etc/wireguard/)."
            )
            row.add_css_class("dim-label")
            self._profiles_group.add(row)
            self._profile_rows.append(row)
            self._status_label.set_label("")
            return

        n = len(self._profiles)
        self._status_label.set_label(
            f"{n} perfil{'is' if n > 1 else ''} encontrado{'s' if n > 1 else ''}."
        )

        for p in self._profiles:
            row = self._build_profile_row(p)
            self._profiles_group.add(row)
            self._profile_rows.append(row)

    def _build_profile_row(self, profile) -> Adw.ExpanderRow:
        is_active = profile.name in self._active_ifaces

        row = Adw.ExpanderRow()
        row.set_title(profile.name)
        subtitle_bits = []
        if is_active:
            subtitle_bits.append("CONECTADO")
        if profile.endpoint:
            subtitle_bits.append(f"endpoint: {profile.endpoint}")
        if profile.address:
            subtitle_bits.append(f"address: {profile.address}")
        row.set_subtitle(" · ".join(subtitle_bits) if subtitle_bits else "(sem detalhes)")

        # Prefix badge
        badge = Gtk.Label(label="ON" if is_active else "off")
        badge.add_css_class("monospace")
        badge.add_css_class("caption-heading")
        badge.add_css_class("success" if is_active else "dim-label")
        badge.set_valign(Gtk.Align.CENTER)
        row.add_prefix(badge)

        # Connect/Disconnect button
        btn = Gtk.Button()
        btn.set_valign(Gtk.Align.CENTER)
        if is_active:
            btn.set_label("Desconectar")
            btn.add_css_class("destructive-action")
            btn.connect("clicked", self._on_disconnect_clicked, profile.name)
        else:
            btn.set_label("Conectar")
            btn.add_css_class("suggested-action")
            btn.connect("clicked", self._on_connect_clicked, profile.name)
        btn.set_sensitive(not self._running)
        row.add_suffix(btn)

        # Details rows
        if profile.dns:
            d_row = Adw.ActionRow(title="DNS")
            d_row.add_css_class("property")
            d_lbl = Gtk.Label(label=profile.dns)
            d_lbl.add_css_class("monospace")
            d_lbl.add_css_class("caption")
            d_row.add_suffix(d_lbl)
            row.add_row(d_row)

        path_row = Adw.ActionRow(title="Arquivo")
        path_row.add_css_class("property")
        path_lbl = Gtk.Label(label=profile.path)
        path_lbl.add_css_class("monospace")
        path_lbl.add_css_class("caption")
        path_row.add_suffix(path_lbl)
        row.add_row(path_row)

        return row

    # ============================================================
    # Connect / Disconnect
    # ============================================================

    def _on_connect_clicked(self, _btn: Gtk.Button, profile_name: str) -> None:
        if self._running:
            return
        self._set_running(True, f"Conectando {profile_name}...")
        threading.Thread(
            target=self._connect_worker, args=(profile_name,), daemon=True
        ).start()

    def _connect_worker(self, profile_name: str) -> None:
        try:
            ok, err = backend.connect_blocking(profile_name)
        except Exception as e:  # pylint: disable=broad-except
            ok, err = False, f"Excecao: {e}"
        GLib.idle_add(self._on_op_done, ok, err, profile_name, "conectar")

    def _on_disconnect_clicked(self, _btn: Gtk.Button, profile_name: str) -> None:
        if self._running:
            return
        self._set_running(True, f"Desconectando {profile_name}...")
        threading.Thread(
            target=self._disconnect_worker, args=(profile_name,), daemon=True
        ).start()

    def _disconnect_worker(self, profile_name: str) -> None:
        try:
            ok, err = backend.disconnect_blocking(profile_name)
        except Exception as e:  # pylint: disable=broad-except
            ok, err = False, f"Excecao: {e}"
        GLib.idle_add(self._on_op_done, ok, err, profile_name, "desconectar")

    def _on_op_done(self, ok: bool, err: str, profile_name: str, op: str) -> bool:
        self._set_running(False)
        if not ok:
            show_error(self, f"Falha ao {op} {profile_name}", err)
        else:
            # Reload active ifaces
            try:
                self._active_ifaces = set(backend.list_active_interfaces())
            except Exception:  # pylint: disable=broad-except
                pass
            self._render_profiles()
        return False

    # ============================================================
    # Import dialog
    # ============================================================

    def _show_import_dialog(self) -> None:
        dlg = Adw.AlertDialog(
            heading="Importar perfil WireGuard",
            body="Cole o conteudo do arquivo .conf abaixo. O Vigia vai salvar "
            "em /etc/wireguard/<nome>.conf via pkexec.",
        )

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        body.set_margin_top(8)
        body.set_margin_bottom(8)

        body.append(Gtk.Label(label="Nome do perfil (sem .conf):"))
        name_entry = Gtk.Entry()
        name_entry.set_placeholder_text("ex: meu-vpn")
        body.append(name_entry)

        # Header do textarea com botao 'Colar' (fallback se Ctrl+V nao funcionar)
        ta_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ta_label = Gtk.Label(label="Conteudo do .conf:")
        ta_label.set_hexpand(True)
        ta_label.set_xalign(0)
        ta_header.append(ta_label)
        paste_btn = Gtk.Button.new_from_icon_name("edit-paste-symbolic")
        paste_btn.set_tooltip_text("Colar da area de transferencia")
        paste_btn.add_css_class("flat")
        ta_header.append(paste_btn)
        body.append(ta_header)

        text_view = Gtk.TextView()
        text_view.set_editable(True)
        text_view.set_can_focus(True)
        text_view.set_accepts_tab(False)
        text_view.set_monospace(True)
        text_view.set_top_margin(8)
        text_view.set_bottom_margin(8)
        text_view.set_left_margin(8)
        text_view.set_right_margin(8)

        # Handler do botao Colar
        def _on_paste_clicked(_btn: Gtk.Button) -> None:
            display = text_view.get_display()
            if display is None:
                return
            clipboard = display.get_clipboard()
            clipboard.read_text_async(None, _on_clipboard_read)

        def _on_clipboard_read(clipboard, result):
            try:
                text = clipboard.read_text_finish(result)
            except Exception:  # pylint: disable=broad-except
                return
            if text:
                buf = text_view.get_buffer()
                buf.set_text(text)

        paste_btn.connect("clicked", _on_paste_clicked)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(180)
        scrolled.set_min_content_width(420)
        scrolled.add_css_class("card")
        scrolled.set_child(text_view)
        body.append(scrolled)

        dlg.set_extra_child(body)
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("import", "Importar")
        dlg.set_default_response("import")
        dlg.set_response_appearance("import", Adw.ResponseAppearance.SUGGESTED)
        dlg.connect("response", self._on_import_response, name_entry, text_view)
        dlg.present(self.get_root())

        # Foco inicial no name_entry para o usuario poder digitar imediatamente.
        # Sem isso, o dialog abria com foco em nenhum lugar, e Ctrl+V no
        # TextView nao funcionava porque o widget nao tinha keyboard focus.
        GLib.idle_add(name_entry.grab_focus)

    def _on_import_response(
        self,
        _dlg,
        response: str,
        name_entry: Gtk.Entry,
        text_view: Gtk.TextView,
    ) -> None:
        if response != "import":
            return
        name = name_entry.get_text().strip()
        buf = text_view.get_buffer()
        content = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
        if not name or not content.strip():
            show_error(self, "Dados invalidos", "Nome e conteudo sao obrigatorios.")
            return

        self._set_running(True, f"Importando {name}...")
        threading.Thread(
            target=self._import_worker, args=(name, content), daemon=True
        ).start()

    def _import_worker(self, name: str, content: str) -> None:
        try:
            ok, err = backend.import_profile_blocking(name, content)
        except Exception as e:  # pylint: disable=broad-except
            ok, err = False, f"Excecao: {e}"
        GLib.idle_add(self._on_import_done, ok, err, name)

    def _on_import_done(self, ok: bool, err: str, name: str) -> bool:
        self._set_running(False)
        if not ok:
            show_error(self, "Falha ao importar", err)
            return False
        show_info(
            self,
            "Perfil importado",
            f"Perfil '{name}' salvo em /etc/wireguard/{name}.conf. "
            "Recarregando lista...",
        )
        self._load_profiles()
        return False

    # ============================================================
    # Running state
    # ============================================================

    def _set_running(self, running: bool, label: str = "") -> None:
        self._running = running
        self._load_btn.set_sensitive(not running)
        self._import_btn.set_sensitive(not running)
        if running:
            self._status_label.set_label(label)
        # Re-render para desabilitar botoes nos rows
        if self._profiles:
            self._render_profiles()
