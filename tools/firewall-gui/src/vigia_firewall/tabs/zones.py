"""Tab Zones: edita services + ports em uma zona selecionada."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from ._helpers import make_clamp, show_error


class ZonesTab(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        inner = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=12,
            margin_top=12, margin_bottom=12, margin_start=12, margin_end=12,
        )
        self.append(make_clamp(inner))

        # ============= Zone selector ============= #
        zone_group = Adw.PreferencesGroup()
        zone_group.set_title("Configurar uma zona")
        zone_group.set_description(
            "Mudanças são --permanent + --reload (persistem no boot e aplicam imediatamente)."
        )

        self._zone_combo = Adw.ComboRow()
        self._zone_combo.set_title("Zona")
        self._zone_model = Gtk.StringList()
        self._zone_combo.set_model(self._zone_model)
        self._suppress_combo = False
        self._zone_combo.connect("notify::selected", self._on_zone_change)
        zone_group.add(self._zone_combo)
        inner.append(zone_group)

        # ============= Services group ============= #
        self._services_group = Adw.PreferencesGroup()
        self._services_group.set_margin_top(24)
        self._services_group.set_title("Services permitidos nesta zona")
        self._services_group.set_description(
            "Services pré-definidos do firewalld. Ex: ssh, http, https, dhcpv6-client."
        )

        # Botao Add Service
        self._add_svc_row = Adw.ActionRow()
        self._add_svc_row.set_title("Adicionar service")
        self._add_svc_btn = Gtk.Button(label="+ Adicionar")
        self._add_svc_btn.set_valign(Gtk.Align.CENTER)
        self._add_svc_btn.add_css_class("suggested-action")
        self._add_svc_btn.connect("clicked", lambda _b: self._show_add_service_dialog())
        self._add_svc_row.add_suffix(self._add_svc_btn)
        self._services_group.add(self._add_svc_row)

        self._service_rows: list[Adw.ActionRow] = []
        inner.append(self._services_group)

        # ============= Ports group ============= #
        self._ports_group = Adw.PreferencesGroup()
        self._ports_group.set_margin_top(24)
        self._ports_group.set_title("Portas permitidas nesta zona")
        self._ports_group.set_description(
            "Portas/protocolo customizados. Use services acima para portas conhecidas."
        )

        self._add_port_row = Adw.ActionRow()
        self._add_port_row.set_title("Adicionar porta")
        self._add_port_btn = Gtk.Button(label="+ Adicionar")
        self._add_port_btn.set_valign(Gtk.Align.CENTER)
        self._add_port_btn.add_css_class("suggested-action")
        self._add_port_btn.connect("clicked", lambda _b: self._show_add_port_dialog())
        self._add_port_row.add_suffix(self._add_port_btn)
        self._ports_group.add(self._add_port_row)

        self._port_rows: list[Adw.ActionRow] = []
        inner.append(self._ports_group)

        # Populate
        self._populate_zones()

    # ========================================================================
    # Population
    # ========================================================================

    def _populate_zones(self) -> None:
        """Coleta zonas + default zone em thread (2 firewall-cmd calls)."""
        threading.Thread(target=self._populate_zones_worker, daemon=True).start()

    def _populate_zones_worker(self) -> None:
        try:
            zones = backend.list_zones()
            default = backend.get_default_zone()
        except Exception:  # pylint: disable=broad-except
            zones, default = [], ""
        GLib.idle_add(self._apply_zones, zones, default)

    def _apply_zones(self, zones: list, default: str) -> bool:
        while self._zone_model.get_n_items() > 0:
            self._zone_model.remove(0)
        idx = 0
        for i, z in enumerate(zones):
            self._zone_model.append(z)
            if z == default:
                idx = i
        self._suppress_combo = True
        self._zone_combo.set_selected(idx)
        self._suppress_combo = False
        if zones:
            self._refresh_zone_contents(zones[idx])
        return False

    def _current_zone(self) -> str:
        idx = self._zone_combo.get_selected()
        if idx >= self._zone_model.get_n_items():
            return ""
        return self._zone_model.get_string(idx)

    def _refresh_zone_contents(self, zone: str) -> None:
        """Dispara fetch async (services + ports da zona via firewall-cmd)."""
        threading.Thread(
            target=self._zone_contents_worker, args=(zone,), daemon=True
        ).start()

    def _zone_contents_worker(self, zone: str) -> None:
        try:
            services = backend.list_zone_services(zone)
            ports = backend.list_zone_ports(zone)
        except Exception:  # pylint: disable=broad-except
            services, ports = [], []
        GLib.idle_add(self._apply_zone_contents, services, ports)

    def _apply_zone_contents(self, services: list, ports: list) -> bool:
        # Services
        for r in self._service_rows:
            self._services_group.remove(r)
        self._service_rows.clear()
        if not services:
            empty = Adw.ActionRow()
            empty.set_title("Nenhum service permitido")
            empty.set_subtitle("Clique em '+ Adicionar' para liberar um service.")
            self._services_group.add(empty)
            self._service_rows.append(empty)
        else:
            for svc in sorted(services):
                row = Adw.ActionRow()
                row.set_title(svc)
                btn = Gtk.Button(label="Remover")
                btn.add_css_class("destructive-action")
                btn.set_valign(Gtk.Align.CENTER)
                btn.connect("clicked", lambda _b, s=svc: self._remove_service(s))
                row.add_suffix(btn)
                self._services_group.add(row)
                self._service_rows.append(row)

        # Ports
        for r in self._port_rows:
            self._ports_group.remove(r)
        self._port_rows.clear()
        if not ports:
            empty = Adw.ActionRow()
            empty.set_title("Nenhuma porta customizada")
            empty.set_subtitle("Clique em '+ Adicionar' para liberar uma porta.")
            self._ports_group.add(empty)
            self._port_rows.append(empty)
        else:
            for p in ports:
                row = Adw.ActionRow()
                row.set_title(p.to_arg())
                row.set_subtitle(f"Porta {p.port} via {p.protocol.upper()}")
                btn = Gtk.Button(label="Remover")
                btn.add_css_class("destructive-action")
                btn.set_valign(Gtk.Align.CENTER)
                btn.connect(
                    "clicked",
                    lambda _b, port=p.port, proto=p.protocol: self._remove_port(port, proto),
                )
                row.add_suffix(btn)
                self._ports_group.add(row)
                self._port_rows.append(row)
        return False

    # ========================================================================
    # Event handlers
    # ========================================================================

    def _on_zone_change(self, combo: Adw.ComboRow, _pspec: object) -> None:
        if self._suppress_combo:
            return
        self._refresh_zone_contents(self._current_zone())

    def _show_add_service_dialog(self) -> None:
        zone = self._current_zone()
        if not zone:
            return
        current = set(backend.list_zone_services(zone))
        available = [s for s in backend.list_available_services() if s not in current]
        if not available:
            show_error(self, "Nenhum service disponível", "Todos já estão permitidos nesta zona.")
            return

        # Cria dialog com combo
        dlg = Adw.AlertDialog(heading=f"Adicionar service na zona '{zone}'")
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                       margin_top=8, margin_bottom=8)
        body.append(Gtk.Label(label="Selecione o service:"))
        combo = Gtk.DropDown.new_from_strings(available)
        body.append(combo)
        dlg.set_extra_child(body)
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("add", "Adicionar")
        dlg.set_default_response("add")
        dlg.set_response_appearance("add", Adw.ResponseAppearance.SUGGESTED)

        def on_response(d: Adw.AlertDialog, response_id: str) -> None:
            if response_id != "add":
                return
            idx = combo.get_selected()
            if idx >= len(available):
                return
            svc = available[idx]
            # add_zone_service faz pkexec — vai pra thread
            threading.Thread(
                target=self._add_service_worker, args=(zone, svc), daemon=True
            ).start()

        dlg.connect("response", on_response)
        dlg.present(self.get_root())

    def _add_service_worker(self, zone: str, svc: str) -> None:
        try:
            backend.add_zone_service(zone, svc)
            err = None
        except Exception as e:  # pylint: disable=broad-except
            err = str(e)
        GLib.idle_add(self._on_service_change_done, zone, svc, err)

    def _show_add_port_dialog(self) -> None:
        zone = self._current_zone()
        if not zone:
            return

        dlg = Adw.AlertDialog(heading=f"Adicionar porta na zona '{zone}'")
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                       margin_top=8, margin_bottom=8)
        body.append(Gtk.Label(label="Porta (ex: 8080 ou range 8000-8010):"))
        port_entry = Gtk.Entry()
        port_entry.set_placeholder_text("8080")
        body.append(port_entry)

        body.append(Gtk.Label(label="Protocolo:"))
        proto_combo = Gtk.DropDown.new_from_strings(["tcp", "udp"])
        body.append(proto_combo)
        dlg.set_extra_child(body)
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("add", "Adicionar")
        dlg.set_default_response("add")
        dlg.set_response_appearance("add", Adw.ResponseAppearance.SUGGESTED)

        def on_response(d: Adw.AlertDialog, response_id: str) -> None:
            if response_id != "add":
                return
            port = port_entry.get_text().strip()
            proto = ["tcp", "udp"][proto_combo.get_selected()]
            threading.Thread(
                target=self._add_port_worker, args=(zone, port, proto), daemon=True
            ).start()

        dlg.connect("response", on_response)
        dlg.present(self.get_root())

    def _add_port_worker(self, zone: str, port: str, proto: str) -> None:
        try:
            backend.add_zone_port(zone, port, proto)
            err = None
        except Exception as e:  # pylint: disable=broad-except
            err = str(e)
        GLib.idle_add(self._on_port_change_done, zone, port, proto, err)

    def _remove_service(self, service: str) -> None:
        """Confirma antes de remover (UX: consistente com outras tools)."""
        zone = self._current_zone()
        dlg = Adw.AlertDialog(
            heading=f"Remover '{service}' da zona '{zone}'?",
            body=(
                "Esta ação remove o service do firewall (--permanent + --reload). "
                "Outras conexões desse service serão bloqueadas pela zona padrão "
                "até você re-adicionar."
            ),
        )
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("remove", "Remover")
        dlg.set_default_response("cancel")
        dlg.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.connect("response", self._on_remove_service_confirmed, zone, service)
        dlg.present(self.get_root())

    def _on_remove_service_confirmed(self, _dlg, response: str, zone: str, service: str) -> None:
        if response != "remove":
            return
        # remove_zone_service faz pkexec firewall-cmd --reload — vai pra thread
        threading.Thread(
            target=self._remove_service_worker, args=(zone, service), daemon=True
        ).start()

    def _remove_service_worker(self, zone: str, service: str) -> None:
        try:
            backend.remove_zone_service(zone, service)
            err = None
        except Exception as e:  # pylint: disable=broad-except
            err = str(e)
        GLib.idle_add(self._on_service_change_done, zone, service, err)

    def _on_service_change_done(self, zone: str, service: str, err: str | None) -> bool:
        if err is not None:
            show_error(self, f"Falha ao operar service '{service}'", err)
        self._refresh_zone_contents(zone)
        return False

    def _remove_port(self, port: str, proto: str) -> None:
        """Confirma antes de remover."""
        zone = self._current_zone()
        dlg = Adw.AlertDialog(
            heading=f"Remover porta {port}/{proto.upper()} da zona '{zone}'?",
            body=(
                "Esta ação remove a porta do firewall (--permanent + --reload). "
                "Conexões nessa porta+protocolo deixarão de ser permitidas."
            ),
        )
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("remove", "Remover")
        dlg.set_default_response("cancel")
        dlg.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.connect("response", self._on_remove_port_confirmed, zone, port, proto)
        dlg.present(self.get_root())

    def _on_remove_port_confirmed(self, _dlg, response: str, zone: str, port: str, proto: str) -> None:
        if response != "remove":
            return
        threading.Thread(
            target=self._remove_port_worker, args=(zone, port, proto), daemon=True
        ).start()

    def _remove_port_worker(self, zone: str, port: str, proto: str) -> None:
        try:
            backend.remove_zone_port(zone, port, proto)
            err = None
        except Exception as e:  # pylint: disable=broad-except
            err = str(e)
        GLib.idle_add(self._on_port_change_done, zone, port, proto, err)

    def _on_port_change_done(
        self, zone: str, port: str, proto: str, err: str | None
    ) -> bool:
        if err is not None:
            show_error(self, f"Falha ao operar porta {port}/{proto}", err)
        self._refresh_zone_contents(zone)
        return False
