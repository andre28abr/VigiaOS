"""Tab Status: estado das conexoes VPN ativas."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from ._helpers import make_clamp


class StatusTab(Adw.Bin):
    """Mostra interfaces WireGuard ativas + peers."""

    def __init__(self) -> None:
        super().__init__()
        self._iface_rows: list = []

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
        self._state_sub.set_max_width_chars(48)

        self._hero.append(self._state_label)
        self._hero.append(self._state_sub)

        # Action row (refresh + admin)
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_halign(Gtk.Align.CENTER)
        action_box.set_margin_bottom(24)

        self._refresh_btn = Gtk.Button(label="Atualizar status")
        self._refresh_btn.connect("clicked", lambda _b: self.refresh(elevated=False))
        action_box.append(self._refresh_btn)

        self._admin_btn = Gtk.Button(label="Detalhes (admin)")
        self._admin_btn.add_css_class("suggested-action")
        self._admin_btn.set_tooltip_text(
            "Le detalhes completos de cada interface via pkexec"
        )
        self._admin_btn.connect("clicked", lambda _b: self.refresh(elevated=True))
        action_box.append(self._admin_btn)

        # Active interfaces group
        self._ifaces_group = Adw.PreferencesGroup()
        self._ifaces_group.set_title("Interfaces ativas")

        # System info group
        self._sys_group = Adw.PreferencesGroup()
        self._sys_group.set_title("Sistema")
        self._wg_row = Adw.ActionRow(title="WireGuard instalado")
        self._wg_row.add_css_class("property")
        self._wg_lbl = Gtk.Label(label="—")
        self._wg_lbl.add_css_class("monospace")
        self._wg_row.add_suffix(self._wg_lbl)
        self._sys_group.add(self._wg_row)

        # Layout
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        outer.set_margin_top(0)
        outer.set_margin_bottom(28)
        outer.set_margin_start(20)
        outer.set_margin_end(20)
        outer.append(self._hero)
        outer.append(action_box)
        outer.append(self._ifaces_group)
        outer.append(self._sys_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

        self.refresh(elevated=False)

    # ============================================================
    # Refresh
    # ============================================================

    def refresh(self, elevated: bool = False) -> None:
        """Coleta status em thread."""
        threading.Thread(target=self._refresh_worker, args=(elevated,), daemon=True).start()

    def _refresh_worker(self, elevated: bool) -> None:
        installed = backend.wireguard_installed()
        ifaces: list[str] = []
        statuses: list[backend.IfaceStatus] = []

        if installed:
            try:
                ifaces = backend.list_active_interfaces()
            except Exception:  # pylint: disable=broad-except
                ifaces = []

            if elevated:
                for iface in ifaces:
                    try:
                        st, _ = backend.get_interface_status_elevated(iface)
                        if st is not None:
                            statuses.append(st)
                    except Exception:  # pylint: disable=broad-except
                        pass

        GLib.idle_add(self._apply, installed, ifaces, statuses)

    def _apply(
        self,
        installed: bool,
        ifaces: list[str],
        statuses: list,
    ) -> bool:
        # System info
        self._wg_lbl.set_label("Sim" if installed else "Nao")
        for cls in ("success", "error"):
            self._wg_lbl.remove_css_class(cls)
        self._wg_lbl.add_css_class("success" if installed else "error")

        # Hero state
        for cls in ("success", "warning", "error", "dim-label"):
            self._state_label.remove_css_class(cls)

        if not installed:
            self._state_label.set_label("WireGuard nao instalado")
            self._state_label.add_css_class("error")
            self._state_sub.set_label(
                "Instale via: rpm-ostree install wireguard-tools && reboot"
            )
        elif not ifaces:
            self._state_label.set_label("Desconectado")
            self._state_label.add_css_class("dim-label")
            self._state_sub.set_label(
                "Nenhuma VPN ativa. Va para a aba 'Perfis' para conectar."
            )
        else:
            self._state_label.set_label("Conectado")
            self._state_label.add_css_class("success")
            n = len(ifaces)
            self._state_sub.set_label(
                f"{n} interface{'s' if n > 1 else ''} ativa{'s' if n > 1 else ''}: "
                + ", ".join(ifaces)
            )

        # Clear and rebuild interfaces group
        for r in self._iface_rows:
            self._ifaces_group.remove(r)
        self._iface_rows = []

        if not ifaces:
            row = Adw.ActionRow(title="Nenhuma interface ativa")
            row.set_subtitle("Conecte um perfil na aba 'Perfis'.")
            row.add_css_class("dim-label")
            self._ifaces_group.add(row)
            self._iface_rows.append(row)
            return False

        # Indexa statuses por iface
        statuses_by_iface = {s.iface: s for s in statuses}

        for iface in ifaces:
            row = Adw.ExpanderRow()
            row.set_title(iface)

            st = statuses_by_iface.get(iface)
            if st is None:
                row.set_subtitle("Clique 'Detalhes (admin)' para ver peers")
            else:
                row.set_subtitle(
                    f"{len(st.peers)} peer{'s' if len(st.peers) > 1 else ''}"
                    + (f" · porta {st.listening_port}" if st.listening_port else "")
                )

                if st.public_key:
                    pub_row = Adw.ActionRow(title="Chave publica (interface)")
                    pub_row.add_css_class("property")
                    pub_lbl = Gtk.Label(label=st.public_key[:24] + "…")
                    pub_lbl.add_css_class("monospace")
                    pub_lbl.add_css_class("caption")
                    pub_row.add_suffix(pub_lbl)
                    row.add_row(pub_row)

                for i, peer in enumerate(st.peers):
                    peer_row = Adw.ActionRow()
                    peer_row.set_title(f"Peer {i + 1}")
                    bits: list[str] = []
                    if peer.get("endpoint"):
                        bits.append(f"endpoint: {peer['endpoint']}")
                    if peer.get("allowed_ips"):
                        bits.append(f"allowed: {peer['allowed_ips']}")
                    if peer.get("latest_handshake"):
                        bits.append(f"ultimo: {peer['latest_handshake']}")
                    if peer.get("rx") or peer.get("tx"):
                        bits.append(f"rx {peer.get('rx', '0 B')} · tx {peer.get('tx', '0 B')}")
                    peer_row.set_subtitle("\n".join(bits))
                    peer_row.set_subtitle_lines(4)
                    row.add_row(peer_row)

            self._ifaces_group.add(row)
            self._iface_rows.append(row)

        return False
