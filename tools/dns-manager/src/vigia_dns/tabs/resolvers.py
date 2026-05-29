"""Tab Provedores (v0.3.0 — dnscrypt-only).

Antes da v0.3 tinha 2 catalogos (DoT do systemd-resolved + dnscrypt).
A v0.3 deixou so o dnscrypt_catalog. UI simplificada — sem mode-aware,
sem cache de IPs (sistema dnscrypt e' rapido pra reportar server ativo
via .toml).
"""

from __future__ import annotations

import re
import threading
import time

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import dnscrypt_backend as dc
from .. import dnscrypt_catalog
from ._helpers import make_clamp, show_error, show_info


def _md_to_pango(md: str) -> str:
    s = md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"`([^`]+)`", r"<tt>\1</tt>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<i>\1</i>", s)
    return s


HEADER_DESC = (
    "Servers <b>dnscrypt-proxy</b> (DoH, DoT, DNSCrypt nativos). Aplicar "
    "edita <tt>server_names</tt> em <tt>/etc/dnscrypt-proxy/dnscrypt-proxy.toml</tt> "
    "e reinicia o serviço. Cada server tem políticas próprias (logs, filtros, "
    "DNSSEC, jurisdição). Recomendado: pelo menos <b>no-logs</b> + <b>DNSSEC</b>."
)


class ResolversTab(Adw.Bin):
    """Catalogo de DNS providers (dnscrypt-only)."""

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._provider_rows: list = []
        # Cache do ultimo server ativo conhecido (sobrevive entre refreshes)
        self._last_active_servers: list[str] = []

        # ===== Header =====
        header_lbl = Gtk.Label(label="Provedores DNS curados")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(8)

        header_desc = Gtk.Label()
        header_desc.set_markup(HEADER_DESC)
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(20)

        # ===== Banner pra estado nao-ativo =====
        self._banner = Adw.Banner()
        self._banner.set_revealed(False)

        # ===== Providers list =====
        self._providers_group = Adw.PreferencesGroup()
        self._providers_group.set_title("Servers dnscrypt-proxy")

        # ===== Layout =====
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(24)
        outer.set_margin_bottom(32)
        outer.set_margin_start(28)
        outer.set_margin_end(28)
        outer.append(header_lbl)
        outer.append(header_desc)
        outer.append(self._providers_group)

        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        container.append(self._banner)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        container.append(scrolled)
        self.set_child(container)

        self.refresh()

    # ============================================================
    # Refresh
    # ============================================================

    def refresh(self, expected_active_servers: list[str] | None = None) -> None:
        """Recarrega catalogo. expected_active_servers eh hint pos-Apply."""
        seed = expected_active_servers
        if seed is None:
            seed = list(self._last_active_servers)
        threading.Thread(
            target=self._refresh_worker, args=(seed,), daemon=True,
        ).start()

    def _refresh_worker(self, expected_servers: list[str]) -> None:
        installed = dc.dnscrypt_installed()
        active = dc.is_active() if installed else False
        active_servers = list(expected_servers)

        if installed:
            try:
                st = dc.get_status()
                for s in st.server_names:
                    if s not in active_servers:
                        active_servers.append(s)
            except Exception as e:  # pylint: disable=broad-except
                print(f"[resolvers] dc.get_status falhou: {e}", flush=True)

        GLib.idle_add(self._apply, installed, active, active_servers)

    def _apply(
        self, installed: bool, active: bool, active_servers: list[str],
    ) -> bool:
        # Atualiza cache apenas com dados nao-vazios
        if active_servers:
            self._last_active_servers = list(active_servers)

        # Banner
        if not installed:
            self._banner.set_title(
                "dnscrypt-proxy não instalado. Instale via Vigia Tool Installer."
            )
            self._banner.set_revealed(True)
        elif not active:
            self._banner.set_title(
                "dnscrypt-proxy instalado mas não ativo. Ative na aba Status."
            )
            self._banner.set_revealed(True)
        else:
            self._banner.set_revealed(False)

        # Limpa rows antigos
        for row in self._provider_rows:
            self._providers_group.remove(row)
        self._provider_rows = []

        # Popula catalogo
        for server in dnscrypt_catalog.SERVERS:
            row = self._build_dnscrypt_row(
                server, active=(active and server.id in active_servers),
            )
            self._providers_group.add(row)
            self._provider_rows.append(row)

        return False

    def _build_dnscrypt_row(
        self, server: dnscrypt_catalog.DnsCryptServer, active: bool = False,
    ) -> Adw.ExpanderRow:
        row = Adw.ExpanderRow()
        row.set_title(server.label)
        sub_bits = [server.provider, server.protocol]
        if server.country:
            sub_bits.append(server.country)
        if active:
            sub_bits.append("ATIVO")
        row.set_subtitle(" · ".join(sub_bits))

        apply_btn = Gtk.Button(label="Em uso" if active else "Aplicar")
        apply_btn.set_valign(Gtk.Align.CENTER)
        if active:
            apply_btn.add_css_class("flat")
            apply_btn.set_sensitive(False)
        else:
            apply_btn.add_css_class("suggested-action")
            apply_btn.connect("clicked", self._on_apply_clicked, server)
        row.add_suffix(apply_btn)

        # Prefix badges
        badges = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        badges.set_valign(Gtk.Align.CENTER)
        if server.no_logs:
            b = Gtk.Label(label="no-logs")
            b.add_css_class("caption")
            b.add_css_class("dim-label")
            badges.append(b)
        if not server.no_filter:
            b = Gtk.Label(label="filtered")
            b.add_css_class("caption")
            b.add_css_class("dim-label")
            badges.append(b)
        if server.dnssec:
            b = Gtk.Label(label="DNSSEC")
            b.add_css_class("caption")
            b.add_css_class("dim-label")
            badges.append(b)
        row.add_prefix(badges)

        # Description (expanded)
        desc_label = Gtk.Label()
        desc_label.set_markup(_md_to_pango(server.description))
        desc_label.set_wrap(True)
        desc_label.set_xalign(0)
        desc_label.set_selectable(True)
        desc_label.set_margin_start(12)
        desc_label.set_margin_end(12)
        desc_label.set_margin_top(8)
        desc_label.set_margin_bottom(12)
        desc_row = Adw.PreferencesRow()
        desc_row.set_child(desc_label)
        desc_row.set_activatable(False)
        row.add_row(desc_row)

        id_row = Adw.ActionRow(title="ID dnscrypt")
        id_row.add_css_class("property")
        id_row.set_subtitle("Nome usado em server_names = [...] do .toml")
        id_lbl = Gtk.Label(label=server.id)
        id_lbl.add_css_class("monospace")
        id_lbl.add_css_class("caption")
        id_row.add_suffix(id_lbl)
        row.add_row(id_row)

        provider_row = Adw.ActionRow(title="Operador")
        provider_row.add_css_class("property")
        provider_lbl = Gtk.Label(
            label=f"{server.provider}" + (f" ({server.country})" if server.country else "")
        )
        provider_lbl.add_css_class("monospace")
        provider_lbl.add_css_class("caption")
        provider_row.add_suffix(provider_lbl)
        row.add_row(provider_row)

        proto_row = Adw.ActionRow(title="Protocolo")
        proto_row.add_css_class("property")
        proto_lbl = Gtk.Label(label=server.protocol)
        proto_lbl.add_css_class("monospace")
        proto_lbl.add_css_class("caption")
        proto_row.add_suffix(proto_lbl)
        row.add_row(proto_row)

        return row

    # ============================================================
    # Apply
    # ============================================================

    def _on_apply_clicked(
        self, _btn: Gtk.Button, server: dnscrypt_catalog.DnsCryptServer,
    ) -> None:
        if self._running:
            return
        dlg = Adw.AlertDialog(
            heading=f"Aplicar {server.label}?",
            body=(
                f"Vai editar /etc/dnscrypt-proxy/dnscrypt-proxy.toml:\n"
                f"  server_names = ['{server.id}']\n\n"
                f"Backup do .toml atual será salvo em "
                f"dnscrypt-proxy.toml.vigia-backup (se não existir).\n\n"
                f"dnscrypt-proxy sera reiniciado.\n\n"
                f"<i>Operador</i>: {server.provider}"
                + (f" ({server.country})" if server.country else "") + "\n"
                f"<i>Protocolo</i>: {server.protocol}"
            ),
        )
        dlg.set_body_use_markup(True)
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("apply", "Aplicar")
        dlg.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("cancel")
        dlg.connect("response", self._on_apply_confirmed, server)
        dlg.present(self.get_root())

    def _on_apply_confirmed(
        self, _dlg, response: str, server: dnscrypt_catalog.DnsCryptServer,
    ) -> None:
        if response != "apply":
            return
        self._running = True
        threading.Thread(
            target=self._apply_worker, args=(server,), daemon=True,
        ).start()

    def _apply_worker(
        self, server: dnscrypt_catalog.DnsCryptServer,
    ) -> None:
        try:
            ok, err = dc.set_servers_blocking([server.id])
        except Exception as e:  # pylint: disable=broad-except
            ok, err = False, f"Excecao: {e}"

        # Poll ate o server.id aparecer em st.server_names (max 3s)
        if ok:
            for _ in range(6):
                try:
                    st = dc.get_status()
                    if server.id in st.server_names:
                        break
                except Exception:  # pylint: disable=broad-except
                    pass
                time.sleep(0.5)
        GLib.idle_add(self._on_apply_done, ok, err, server)

    def _on_apply_done(
        self, ok: bool, err: str, server: dnscrypt_catalog.DnsCryptServer,
    ) -> bool:
        self._running = False
        if not ok:
            show_error(self, f"Falha ao aplicar {server.label}", err)
        else:
            show_info(
                self,
                f"{server.label} ativo",
                f"dnscrypt-proxy reconfigurado para usar '{server.id}'. "
                "Vá para a aba Status para verificar.",
            )
            # Refresh com hint pra UI ja marcar como ATIVO
            self.refresh(expected_active_servers=[server.id])
        return False
