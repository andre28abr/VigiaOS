"""Tab Status: estado atual dos resolvers DNS."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from .._resolvers_module import find_resolver_for_servers
from ._helpers import make_clamp, show_error, show_info


class StatusTab(Adw.Bin):
    """Hero + interfaces + acoes (flush, restore)."""

    def __init__(self) -> None:
        super().__init__()
        self._iface_rows: list = []
        self._running = False

        # Hero
        self._hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._hero.set_halign(Gtk.Align.CENTER)
        self._hero.set_margin_top(32)
        self._hero.set_margin_bottom(20)

        self._state_label = Gtk.Label(label="Verificando...")
        self._state_label.add_css_class("title-1")
        self._state_label.set_halign(Gtk.Align.CENTER)

        self._state_sub = Gtk.Label(label="")
        self._state_sub.add_css_class("title-4")
        self._state_sub.add_css_class("dim-label")
        self._state_sub.set_halign(Gtk.Align.CENTER)
        self._state_sub.set_wrap(True)
        self._state_sub.set_justify(Gtk.Justification.CENTER)
        self._state_sub.set_max_width_chars(56)

        self._hero.append(self._state_label)
        self._hero.append(self._state_sub)

        # Action bar
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_halign(Gtk.Align.CENTER)
        action_box.set_margin_bottom(20)

        self._refresh_btn = Gtk.Button(label="Atualizar")
        self._refresh_btn.connect("clicked", lambda _b: self.refresh())
        action_box.append(self._refresh_btn)

        self._flush_btn = Gtk.Button(label="Limpar cache DNS")
        self._flush_btn.connect("clicked", self._on_flush_clicked)
        action_box.append(self._flush_btn)

        self._restore_btn = Gtk.Button(label="Restaurar padrao")
        self._restore_btn.add_css_class("destructive-action")
        self._restore_btn.set_tooltip_text(
            "Restaura /etc/systemd/resolved.conf do backup (se houver)"
        )
        self._restore_btn.connect("clicked", self._on_restore_clicked)
        action_box.append(self._restore_btn)

        # Global config group
        self._global_group = Adw.PreferencesGroup()
        self._global_group.set_title("Configuracao global")

        self._row_dns = Adw.ActionRow(title="DNS configurado")
        self._row_dns.add_css_class("property")
        self._lbl_dns = Gtk.Label(label="—")
        self._lbl_dns.add_css_class("monospace")
        self._lbl_dns.set_selectable(True)
        self._row_dns.add_suffix(self._lbl_dns)
        self._global_group.add(self._row_dns)

        self._row_provider = Adw.ActionRow(title="Provedor identificado")
        self._row_provider.add_css_class("property")
        self._lbl_provider = Gtk.Label(label="—")
        self._lbl_provider.add_css_class("monospace")
        self._row_provider.add_suffix(self._lbl_provider)
        self._global_group.add(self._row_provider)

        self._row_dot = Adw.ActionRow(title="DNS over TLS (DoT)")
        self._row_dot.add_css_class("property")
        self._row_dot.set_subtitle("Encripta as queries entre voce e o resolver")
        self._lbl_dot = Gtk.Label(label="—")
        self._lbl_dot.add_css_class("monospace")
        self._row_dot.add_suffix(self._lbl_dot)
        self._global_group.add(self._row_dot)

        # Interfaces group
        self._ifaces_group = Adw.PreferencesGroup()
        self._ifaces_group.set_title("Interfaces de rede")
        self._ifaces_group.set_description(
            "DNS configurado por interface (NetworkManager/dhcpcd) — sobrescreve o global."
        )

        # System info
        self._sys_group = Adw.PreferencesGroup()
        self._sys_group.set_title("Sistema")
        self._row_resolved = Adw.ActionRow(title="systemd-resolved")
        self._row_resolved.add_css_class("property")
        self._lbl_resolved = Gtk.Label(label="—")
        self._lbl_resolved.add_css_class("monospace")
        self._row_resolved.add_suffix(self._lbl_resolved)
        self._sys_group.add(self._row_resolved)

        # Layout
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        outer.set_margin_top(0)
        outer.set_margin_bottom(28)
        outer.set_margin_start(20)
        outer.set_margin_end(20)
        outer.append(self._hero)
        outer.append(action_box)
        outer.append(self._global_group)
        outer.append(self._ifaces_group)
        outer.append(self._sys_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

        self.refresh()

    # ============================================================
    # Refresh (async — resolvectl pode ser lento em sistemas estresados)
    # ============================================================

    def refresh(self) -> None:
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        try:
            st = backend.get_status()
        except Exception:  # pylint: disable=broad-except
            st = backend.ResolvedStatus()
        GLib.idle_add(self._apply, st)

    def _apply(self, st: backend.ResolvedStatus) -> bool:
        # Hero
        for cls in ("success", "warning", "error", "dim-label"):
            self._state_label.remove_css_class(cls)

        if not st.available:
            self._state_label.set_label("systemd-resolved nao disponivel")
            self._state_label.add_css_class("error")
            self._state_sub.set_label(
                "Comando 'resolvectl' nao encontrado. Em Silverblue ja vem por padrao."
            )
        elif not st.active:
            self._state_label.set_label("systemd-resolved parado")
            self._state_label.add_css_class("warning")
            self._state_sub.set_label(
                "Service nao esta running. Tente: sudo systemctl start systemd-resolved"
            )
        elif not st.current_dns and not st.global_dns:
            self._state_label.set_label("Sem DNS configurado")
            self._state_label.add_css_class("warning")
            self._state_sub.set_label(
                "Nenhum resolver detectado. Use a aba 'Resolvers' para escolher um."
            )
        else:
            provider = find_resolver_for_servers(
                st.current_dns or st.global_dns
            )
            if provider:
                self._state_label.set_label(provider.name)
                self._state_label.add_css_class("success")
                self._state_sub.set_label(provider.description)
            else:
                self._state_label.set_label("DNS configurado")
                self._state_label.add_css_class("success")
                primary = (st.current_dns or st.global_dns)[0]
                self._state_sub.set_label(f"Usando: {primary}")

        # Sistema
        for cls in ("success", "error", "warning"):
            self._lbl_resolved.remove_css_class(cls)
        if st.active:
            self._lbl_resolved.set_label("ativo")
            self._lbl_resolved.add_css_class("success")
        elif st.available:
            self._lbl_resolved.set_label("parado")
            self._lbl_resolved.add_css_class("warning")
        else:
            self._lbl_resolved.set_label("indisponivel")
            self._lbl_resolved.add_css_class("error")

        # Global config
        if st.global_dns:
            self._lbl_dns.set_label(", ".join(st.global_dns))
        else:
            self._lbl_dns.set_label("(nenhum no [Resolve] config)")
            self._lbl_dns.add_css_class("dim-label")

        provider = find_resolver_for_servers(st.current_dns or st.global_dns)
        if provider:
            self._lbl_provider.set_label(provider.name)
            self._lbl_provider.remove_css_class("dim-label")
        else:
            self._lbl_provider.set_label("(desconhecido)")
            self._lbl_provider.add_css_class("dim-label")

        for cls in ("success", "warning", "dim-label"):
            self._lbl_dot.remove_css_class(cls)
        if st.global_dot == "yes":
            self._lbl_dot.set_label("habilitado")
            self._lbl_dot.add_css_class("success")
        elif st.global_dot == "no":
            self._lbl_dot.set_label("desabilitado")
            self._lbl_dot.add_css_class("warning")
        else:
            self._lbl_dot.set_label("(default)")
            self._lbl_dot.add_css_class("dim-label")

        # Interfaces
        for r in self._iface_rows:
            self._ifaces_group.remove(r)
        self._iface_rows = []

        if not st.interfaces:
            row = Adw.ActionRow(title="Nenhuma interface")
            row.set_subtitle(
                "DNS so do [Global]. Em redes domesticas, o NetworkManager "
                "tipicamente fornece DNS por interface — verifique o roteador."
            )
            row.add_css_class("dim-label")
            self._ifaces_group.add(row)
            self._iface_rows.append(row)
        else:
            for iface in st.interfaces:
                row = Adw.ExpanderRow()
                row.set_title(iface.name)
                if iface.dns_servers:
                    row.set_subtitle(", ".join(iface.dns_servers))
                else:
                    row.set_subtitle("(sem DNS na interface)")

                if iface.dns_over_tls:
                    dot_row = Adw.ActionRow(title="DNS over TLS")
                    dot_row.add_css_class("property")
                    dot_lbl = Gtk.Label(label=iface.dns_over_tls)
                    dot_lbl.add_css_class("monospace")
                    if iface.dns_over_tls == "yes":
                        dot_lbl.add_css_class("success")
                    else:
                        dot_lbl.add_css_class("dim-label")
                    dot_row.add_suffix(dot_lbl)
                    row.add_row(dot_row)

                if iface.domains:
                    dom_row = Adw.ActionRow(title="Search domains")
                    dom_row.add_css_class("property")
                    dom_lbl = Gtk.Label(label=", ".join(iface.domains))
                    dom_lbl.add_css_class("monospace")
                    dom_row.add_suffix(dom_lbl)
                    row.add_row(dom_row)

                self._ifaces_group.add(row)
                self._iface_rows.append(row)

        return False

    # ============================================================
    # Flush cache
    # ============================================================

    def _on_flush_clicked(self, _btn: Gtk.Button) -> None:
        if self._running:
            return
        self._running = True
        self._flush_btn.set_sensitive(False)
        threading.Thread(target=self._flush_worker, daemon=True).start()

    def _flush_worker(self) -> None:
        try:
            ok, err = backend.flush_cache_elevated()
        except Exception as e:  # pylint: disable=broad-except
            ok, err = False, f"Excecao: {e}"
        GLib.idle_add(self._on_flush_done, ok, err)

    def _on_flush_done(self, ok: bool, err: str) -> bool:
        self._running = False
        self._flush_btn.set_sensitive(True)
        if not ok:
            show_error(self, "Falha ao limpar cache", err)
        else:
            show_info(
                self, "Cache limpo",
                "Cache DNS do systemd-resolved foi esvaziado. Proximas "
                "queries vao buscar de novo nos upstream resolvers.",
            )
        return False

    # ============================================================
    # Restore default config
    # ============================================================

    def _on_restore_clicked(self, _btn: Gtk.Button) -> None:
        dlg = Adw.AlertDialog(
            heading="Restaurar /etc/systemd/resolved.conf padrao?",
            body=(
                "Se existir backup criado pelo Vigia "
                "(/etc/systemd/resolved.conf.vigia-backup), restaura ele. "
                "Senao, escreve um config vazio (defaults do systemd-resolved).\n\n"
                "Em ambos os casos, o servico e' reiniciado."
            ),
        )
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("restore", "Restaurar")
        dlg.set_response_appearance("restore", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("cancel")
        dlg.connect("response", self._on_restore_confirmed)
        dlg.present(self.get_root())

    def _on_restore_confirmed(self, _dlg, response: str) -> None:
        if response != "restore":
            return
        self._running = True
        self._restore_btn.set_sensitive(False)
        threading.Thread(target=self._restore_worker, daemon=True).start()

    def _restore_worker(self) -> None:
        try:
            ok, err = backend.restore_default_elevated()
        except Exception as e:  # pylint: disable=broad-except
            ok, err = False, f"Excecao: {e}"
        GLib.idle_add(self._on_restore_done, ok, err)

    def _on_restore_done(self, ok: bool, err: str) -> bool:
        self._running = False
        self._restore_btn.set_sensitive(True)
        if not ok:
            show_error(self, "Falha ao restaurar", err)
        else:
            show_info(
                self, "Config restaurado",
                "systemd-resolved reiniciado. DNS volta aos defaults do sistema.",
            )
            self.refresh()
        return False
