"""Tab Resolvers: catalogo de provedores DNS + apply."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from .._resolvers_module import CATALOG, DnsResolver
from ._helpers import make_clamp, show_error, show_info


# Markdown leve compartilhado
import re


def _md_to_pango(md: str) -> str:
    s = md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"`([^`]+)`", r"<tt>\1</tt>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<i>\1</i>", s)
    return s


FILTER_LABELS = {
    "malware": "🛡 malware",
    "ads": "🚫 ads",
    "trackers": "👁 trackers",
    "adult": "🔞 adulto",
}


class ResolversTab(Adw.Bin):
    """Lista de DNS providers + apply button."""

    def __init__(self) -> None:
        super().__init__()
        self._running = False

        # Header
        header_lbl = Gtk.Label(label="Provedores DNS curados")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(4)

        header_desc = Gtk.Label(
            label=(
                "Cada provedor tem politicas de privacidade e filtros diferentes. "
                "Aplicar muda /etc/systemd/resolved.conf via pkexec e reinicia "
                "o servico. DNS over TLS e' ligado quando o provedor suportar."
            )
        )
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(20)

        # Switch DoT
        dot_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        dot_box.set_margin_bottom(20)
        dot_box.add_css_class("card")
        dot_lbl = Gtk.Label()
        dot_lbl.set_markup(
            "<b>DNS over TLS</b> — encripta queries entre voce e o resolver. "
            "Recomendado <i>ON</i>. Default: ON."
        )
        dot_lbl.set_wrap(True)
        dot_lbl.set_xalign(0)
        dot_lbl.set_hexpand(True)
        dot_lbl.set_margin_start(12)
        dot_lbl.set_margin_top(12)
        dot_lbl.set_margin_bottom(12)
        dot_box.append(dot_lbl)

        self._dot_switch = Gtk.Switch()
        self._dot_switch.set_valign(Gtk.Align.CENTER)
        self._dot_switch.set_margin_end(12)
        self._dot_switch.set_active(True)
        dot_box.append(self._dot_switch)

        # Providers list
        self._providers_group = Adw.PreferencesGroup()
        self._providers_group.set_title("Provedores")

        for resolver in CATALOG:
            self._providers_group.add(self._build_provider_row(resolver))

        # Layout
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(20)
        outer.set_margin_bottom(20)
        outer.set_margin_start(20)
        outer.set_margin_end(20)
        outer.append(header_lbl)
        outer.append(header_desc)
        outer.append(dot_box)
        outer.append(self._providers_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

    # ============================================================
    # Provider row
    # ============================================================

    def _build_provider_row(self, resolver: DnsResolver) -> Adw.ExpanderRow:
        row = Adw.ExpanderRow()
        row.set_title(resolver.name)
        row.set_subtitle(resolver.description)

        # Apply button
        apply_btn = Gtk.Button(label="Aplicar")
        apply_btn.set_valign(Gtk.Align.CENTER)
        apply_btn.add_css_class("suggested-action")
        apply_btn.connect("clicked", self._on_apply_clicked, resolver)
        row.add_suffix(apply_btn)

        # Filter badges as prefix
        if resolver.filters:
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            box.set_valign(Gtk.Align.CENTER)
            for f in resolver.filters[:3]:
                pill = Gtk.Label(label=FILTER_LABELS.get(f, f))
                pill.add_css_class("monospace")
                pill.add_css_class("caption")
                pill.add_css_class("dim-label")
                box.append(pill)
            row.add_prefix(box)

        # Details (expanded)
        why_label = Gtk.Label()
        why_label.set_markup(_md_to_pango(resolver.why))
        why_label.set_wrap(True)
        why_label.set_xalign(0)
        why_label.set_selectable(True)
        why_label.set_margin_start(12)
        why_label.set_margin_end(12)
        why_label.set_margin_top(8)
        why_label.set_margin_bottom(12)
        why_row = Adw.PreferencesRow()
        why_row.set_child(why_label)
        why_row.set_activatable(False)
        row.add_row(why_row)

        # IPs row
        ips_row = Adw.ActionRow(title="Servidores IPv4")
        ips_row.add_css_class("property")
        ips_lbl = Gtk.Label(label=", ".join(resolver.servers_v4))
        ips_lbl.add_css_class("monospace")
        ips_lbl.add_css_class("caption")
        ips_row.add_suffix(ips_lbl)
        row.add_row(ips_row)

        # Protocols row
        protos: list[str] = []
        if resolver.supports_dot:
            protos.append("DoT")
        if resolver.supports_doh:
            protos.append("DoH")
        if not protos:
            protos.append("plaintext only")
        proto_row = Adw.ActionRow(title="Protocolos suportados")
        proto_row.add_css_class("property")
        proto_lbl = Gtk.Label(label=" · ".join(protos))
        proto_lbl.add_css_class("monospace")
        proto_lbl.add_css_class("caption")
        proto_row.add_suffix(proto_lbl)
        row.add_row(proto_row)

        return row

    # ============================================================
    # Apply
    # ============================================================

    def _on_apply_clicked(self, _btn: Gtk.Button, resolver: DnsResolver) -> None:
        if self._running:
            return

        dlg = Adw.AlertDialog(
            heading=f"Aplicar {resolver.name}?",
            body=(
                f"Vai escrever /etc/systemd/resolved.conf com:\n"
                f"  DNS = {' '.join(resolver.servers_v4)}\n"
                f"  DNSOverTLS = {'yes' if self._dot_switch.get_active() and resolver.supports_dot else 'no'}\n\n"
                "Backup do config atual sera salvo em "
                "/etc/systemd/resolved.conf.vigia-backup (se nao existir).\n\n"
                "systemd-resolved sera reiniciado."
            ),
        )
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("apply", "Aplicar")
        dlg.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("cancel")
        dlg.connect("response", self._on_apply_confirmed, resolver)
        dlg.present(self.get_root())

    def _on_apply_confirmed(
        self, _dlg, response: str, resolver: DnsResolver
    ) -> None:
        if response != "apply":
            return
        use_dot = self._dot_switch.get_active() and resolver.supports_dot
        self._running = True
        threading.Thread(
            target=self._apply_worker, args=(resolver, use_dot), daemon=True
        ).start()

    def _apply_worker(self, resolver: DnsResolver, use_dot: bool) -> None:
        try:
            ok, err = backend.set_global_dns_elevated(
                servers=resolver.servers_v4,
                dot=use_dot,
            )
        except Exception as e:  # pylint: disable=broad-except
            ok, err = False, f"Excecao: {e}"
        GLib.idle_add(self._on_apply_done, ok, err, resolver)

    def _on_apply_done(self, ok: bool, err: str, resolver: DnsResolver) -> bool:
        self._running = False
        if not ok:
            show_error(self, f"Falha ao aplicar {resolver.name}", err)
        else:
            show_info(
                self,
                f"{resolver.name} ativo",
                f"DNS configurado pra usar {' / '.join(resolver.servers_v4)}. "
                "Va para a aba Status para verificar.",
            )
        return False
