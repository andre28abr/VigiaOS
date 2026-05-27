"""Tab Resolvers/Provedores: catalogo de DNS providers + apply.

v0.2.3: mode-aware. Conteudo adapta ao backend ativo:

- Modo simples (systemd-resolved):
    Mostra catalogo DoT classico (9 providers do _resolvers_module).
    DoT switch no topo. Apply edita /etc/systemd/resolved.conf.

- Modo avancado (dnscrypt-proxy):
    Mostra catalogo dnscrypt-proxy (11 servers de dnscrypt_catalog).
    Sem DoT switch (todos sao DoH/DoT/DNSCrypt nativos). Apply
    edita server_names = [...] em /etc/dnscrypt-proxy/dnscrypt-proxy.toml.

Refresh chamado pelo window.py quando user troca de tab ou quando
mode muda (callback do StatusTab).
"""

from __future__ import annotations

import re
import threading
import time

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from .. import dnscrypt_backend as dc
from .. import dnscrypt_catalog
from .. import migration
from .._resolvers_module import CATALOG, DnsResolver
from ._helpers import make_clamp, show_error, show_info


# Markdown leve compartilhado
def _md_to_pango(md: str) -> str:
    s = md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"`([^`]+)`", r"<tt>\1</tt>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<i>\1</i>", s)
    return s


# Badges para o modo simples (CATALOG.filters)
FILTER_LABELS = {
    "malware": "🛡 malware",
    "ads": "🚫 ads",
    "trackers": "👁 trackers",
    "adult": "🔞 adulto",
}


# Headers diferenciados por modo
HEADER_SIMPLE = (
    "Cada provedor tem politicas de privacidade e filtros diferentes. "
    "Aplicar muda /etc/systemd/resolved.conf via pkexec e reinicia "
    "o servico. DNS over TLS e' ligado quando o provedor suportar."
)

HEADER_ADVANCED = (
    "Servers dnscrypt-proxy (DoH, DNSCrypt). Aplicar edita "
    "server_names em /etc/dnscrypt-proxy/dnscrypt-proxy.toml e "
    "reinicia o servico. Cada server tem politicas proprias."
)


class ResolversTab(Adw.Bin):
    """Catalogo de DNS providers — adapta ao modo ativo."""

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._current_mode = "unknown"
        self._provider_rows: list = []

        # ===== Header (mode-aware via refresh) =====
        self._header_lbl = Gtk.Label(label="Provedores DNS curados")
        self._header_lbl.add_css_class("title-2")
        self._header_lbl.set_halign(Gtk.Align.START)
        self._header_lbl.set_margin_bottom(8)

        self._header_desc = Gtk.Label(label=HEADER_SIMPLE)
        self._header_desc.add_css_class("dim-label")
        self._header_desc.set_halign(Gtk.Align.START)
        self._header_desc.set_wrap(True)
        self._header_desc.set_xalign(0)
        self._header_desc.set_margin_bottom(20)

        # ===== Switch DoT (visivel so em modo simples) =====
        self._dot_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self._dot_container.set_margin_bottom(20)
        self._dot_container.add_css_class("card")

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
        self._dot_container.append(dot_lbl)

        self._dot_switch = Gtk.Switch()
        self._dot_switch.set_valign(Gtk.Align.CENTER)
        self._dot_switch.set_margin_end(12)
        self._dot_switch.set_active(True)
        self._dot_container.append(self._dot_switch)

        # ===== Providers list (populado dinamicamente em _apply_mode) =====
        self._providers_group = Adw.PreferencesGroup()
        self._providers_group.set_title("Provedores")

        # ===== Layout =====
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(24)
        outer.set_margin_bottom(32)
        outer.set_margin_start(28)
        outer.set_margin_end(28)
        outer.append(self._header_lbl)
        outer.append(self._header_desc)
        outer.append(self._dot_container)
        outer.append(self._providers_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

        # Carrega catalogo inicial
        self.refresh()

    # ============================================================
    # Refresh — detecta modo e atualiza catalogo
    # ============================================================

    def refresh(
        self,
        expected_active_ips: list[str] | None = None,
        expected_active_servers: list[str] | None = None,
    ) -> None:
        """Recarrega catalogo baseado no modo ativo.

        v0.2.6: aceita hints `expected_active_*` que sao usados como
        seed do estado active. Permite que apos um Apply bem-sucedido a
        UI ja reflita o novo estado MESMO SE `backend.get_status()`
        ainda nao retornar dados frescos (race com restart do servico).
        Sem hints, comporta-se como antes (so consulta o sistema).
        """
        threading.Thread(
            target=self._refresh_worker,
            args=(expected_active_ips or [], expected_active_servers or []),
            daemon=True,
        ).start()

    def _refresh_worker(
        self,
        expected_ips: list[str],
        expected_servers: list[str],
    ) -> None:
        try:
            mode = migration.get_current_mode()
        except Exception as e:  # pylint: disable=broad-except
            print(f"[resolvers] get_current_mode falhou: {e}", flush=True)
            mode = "unknown"

        # Seed com os hints (optimistic update). Mesmo se o sistema
        # retornar vazio (race), a UI marca o resolver aplicado.
        active_servers: list[str] = list(expected_servers)
        active_dns_ips: list[str] = list(expected_ips)

        if mode == "advanced":
            try:
                st = dc.get_status()
                for s in st.server_names:
                    if s not in active_servers:
                        active_servers.append(s)
            except Exception as e:  # pylint: disable=broad-except
                print(f"[resolvers] dc.get_status falhou: {e}", flush=True)
        else:
            # Modo simples: usa resolvectl status para descobrir DNS atual
            try:
                st = backend.get_status()
                for ip in (st.current_dns + st.global_dns):
                    if ip not in active_dns_ips:
                        active_dns_ips.append(ip)
            except Exception as e:  # pylint: disable=broad-except
                print(f"[resolvers] backend.get_status falhou: {e}", flush=True)

        GLib.idle_add(self._apply_mode, mode, active_servers, active_dns_ips)

    def _apply_mode(
        self, mode: str,
        active_servers: list[str],
        active_dns_ips: list[str],
    ) -> bool:
        # Sempre re-renderiza ao trocar de modo, OU se active state pode
        # ter mudado (refresh chamado apos Apply ou ao trocar de tab).
        # Rebuild simples mas garantido — evita estado stale.

        self._current_mode = mode

        # Limpa rows antigos
        for row in self._provider_rows:
            self._providers_group.remove(row)
        self._provider_rows = []

        is_advanced = (mode == "advanced")

        # DoT switch so em modo simples
        self._dot_container.set_visible(not is_advanced)

        # Header descricao
        self._header_desc.set_label(
            HEADER_ADVANCED if is_advanced else HEADER_SIMPLE
        )

        # Title do group
        self._providers_group.set_title(
            "Servers dnscrypt-proxy" if is_advanced else "Provedores"
        )

        # Popula catalogo apropriado
        if is_advanced:
            for server in dnscrypt_catalog.SERVERS:
                row = self._build_dnscrypt_row(
                    server, active=server.id in active_servers,
                )
                self._providers_group.add(row)
                self._provider_rows.append(row)
        else:
            active_ip_set = set(active_dns_ips)
            for resolver in CATALOG:
                # Considera "ativo" se ALGUM IP do resolver bate com active DNS
                is_active = any(s in active_ip_set for s in resolver.servers_v4)
                row = self._build_dot_row(resolver, active=is_active)
                self._providers_group.add(row)
                self._provider_rows.append(row)

        return False

    # ============================================================
    # Build row — Modo simples (systemd-resolved DoT)
    # ============================================================

    def _build_dot_row(
        self, resolver: DnsResolver, active: bool = False,
    ) -> Adw.ExpanderRow:
        row = Adw.ExpanderRow()
        row.set_title(resolver.name)
        sub = resolver.description
        if active:
            sub = f"ATIVO · {sub}"
        row.set_subtitle(sub)

        # Apply button — vira "Em uso" (flat, disabled) se ja ativo
        if active:
            apply_btn = Gtk.Button(label="Em uso")
            apply_btn.add_css_class("flat")
            apply_btn.set_sensitive(False)
        else:
            apply_btn = Gtk.Button(label="Aplicar")
            apply_btn.add_css_class("suggested-action")
            apply_btn.connect("clicked", self._on_apply_dot_clicked, resolver)
        apply_btn.set_valign(Gtk.Align.CENTER)
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

        # Details
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

        ips_row = Adw.ActionRow(title="Servidores IPv4")
        ips_row.add_css_class("property")
        ips_lbl = Gtk.Label(label=", ".join(resolver.servers_v4))
        ips_lbl.add_css_class("monospace")
        ips_lbl.add_css_class("caption")
        ips_row.add_suffix(ips_lbl)
        row.add_row(ips_row)

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
    # Build row — Modo avancado (dnscrypt-proxy)
    # ============================================================

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

        # Apply button (com label diferente se ja ativo)
        apply_btn = Gtk.Button(label="Em uso" if active else "Aplicar")
        apply_btn.set_valign(Gtk.Align.CENTER)
        if active:
            apply_btn.add_css_class("flat")
            apply_btn.set_sensitive(False)
        else:
            apply_btn.add_css_class("suggested-action")
            apply_btn.connect("clicked", self._on_apply_dnscrypt_clicked, server)
        row.add_suffix(apply_btn)

        # Prefix badges
        badges = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        badges.set_valign(Gtk.Align.CENTER)

        if server.no_logs:
            b = Gtk.Label(label="🔒 no-logs")
            b.add_css_class("caption")
            b.add_css_class("dim-label")
            badges.append(b)

        if not server.no_filter:
            b = Gtk.Label(label="🛡 filtered")
            b.add_css_class("caption")
            b.add_css_class("dim-label")
            badges.append(b)

        if server.dnssec:
            b = Gtk.Label(label="🔐 DNSSEC")
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

        # ID dnscrypt (server name no config)
        id_row = Adw.ActionRow(title="ID dnscrypt")
        id_row.add_css_class("property")
        id_row.set_subtitle("Nome usado em server_names = [...] do .toml")
        id_lbl = Gtk.Label(label=server.id)
        id_lbl.add_css_class("monospace")
        id_lbl.add_css_class("caption")
        id_row.add_suffix(id_lbl)
        row.add_row(id_row)

        # Provider info
        provider_row = Adw.ActionRow(title="Operador")
        provider_row.add_css_class("property")
        provider_lbl = Gtk.Label(
            label=f"{server.provider}" + (f" ({server.country})" if server.country else "")
        )
        provider_lbl.add_css_class("monospace")
        provider_lbl.add_css_class("caption")
        provider_row.add_suffix(provider_lbl)
        row.add_row(provider_row)

        # Protocol
        proto_row = Adw.ActionRow(title="Protocolo")
        proto_row.add_css_class("property")
        proto_lbl = Gtk.Label(label=server.protocol)
        proto_lbl.add_css_class("monospace")
        proto_lbl.add_css_class("caption")
        proto_row.add_suffix(proto_lbl)
        row.add_row(proto_row)

        return row

    # ============================================================
    # Apply — Modo simples (systemd-resolved)
    # ============================================================

    def _on_apply_dot_clicked(self, _btn: Gtk.Button, resolver: DnsResolver) -> None:
        if self._running:
            return

        dlg = Adw.AlertDialog(
            heading=f"Aplicar {resolver.name}?",
            body=(
                f"Vai escrever /etc/systemd/resolved.conf com:\n"
                f"  DNS = {' '.join(resolver.servers_v4)}\n"
                f"  DNSOverTLS = "
                f"{'yes' if self._dot_switch.get_active() and resolver.supports_dot else 'no'}\n"
                f"  Domains = ~. (forca DNS global em todas as queries)\n\n"
                "Backup do config atual sera salvo em "
                "/etc/systemd/resolved.conf.vigia-backup (se nao existir).\n\n"
                "systemd-resolved sera reiniciado e o cache limpo."
            ),
        )
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("apply", "Aplicar")
        dlg.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("cancel")
        dlg.connect("response", self._on_apply_dot_confirmed, resolver)
        dlg.present(self.get_root())

    def _on_apply_dot_confirmed(
        self, _dlg, response: str, resolver: DnsResolver
    ) -> None:
        if response != "apply":
            return
        use_dot = self._dot_switch.get_active() and resolver.supports_dot
        self._running = True
        threading.Thread(
            target=self._apply_dot_worker, args=(resolver, use_dot), daemon=True
        ).start()

    def _apply_dot_worker(self, resolver: DnsResolver, use_dot: bool) -> None:
        try:
            ok, err = backend.set_global_dns_elevated(
                servers=resolver.servers_v4,
                dot=use_dot,
            )
        except Exception as e:  # pylint: disable=broad-except
            ok, err = False, f"Excecao: {e}"

        # v0.2.6: poll ate `global_dns` ficar populado (max 3s, 6 tentativas
        # de 0.5s). Mesmo se ele NUNCA aparecer (sistema lento, NM nao
        # propagou), o `expected_active_ips` do refresh ja vai marcar.
        if ok:
            for _ in range(6):
                try:
                    st = backend.get_status()
                    if st.global_dns:
                        break
                except Exception:  # pylint: disable=broad-except
                    pass
                time.sleep(0.5)
        GLib.idle_add(self._on_apply_dot_done, ok, err, resolver)

    def _on_apply_dot_done(
        self, ok: bool, err: str, resolver: DnsResolver
    ) -> bool:
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
            # v0.2.6: passa os IPs do resolver como expected_active_ips.
            # Mesmo se resolvectl ainda nao tiver atualizado (race com
            # restart do systemd-resolved), o botao ja vai mostrar
            # "Em uso" imediatamente.
            self.refresh(expected_active_ips=list(resolver.servers_v4))
        return False

    # ============================================================
    # Apply — Modo avancado (dnscrypt-proxy)
    # ============================================================

    def _on_apply_dnscrypt_clicked(
        self, _btn: Gtk.Button, server: dnscrypt_catalog.DnsCryptServer,
    ) -> None:
        if self._running:
            return

        dlg = Adw.AlertDialog(
            heading=f"Aplicar {server.label}?",
            body=(
                f"Vai editar /etc/dnscrypt-proxy/dnscrypt-proxy.toml:\n"
                f"  server_names = ['{server.id}']\n\n"
                f"Backup do .toml atual sera salvo em "
                f"dnscrypt-proxy.toml.vigia-backup (se nao existir).\n\n"
                f"dnscrypt-proxy sera reiniciado.\n\n"
                f"<i>Operador</i>: {server.provider} ({server.country})\n"
                f"<i>Protocolo</i>: {server.protocol}"
            ),
        )
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("apply", "Aplicar")
        dlg.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("cancel")
        dlg.connect("response", self._on_apply_dnscrypt_confirmed, server)
        dlg.present(self.get_root())

    def _on_apply_dnscrypt_confirmed(
        self, _dlg, response: str, server: dnscrypt_catalog.DnsCryptServer,
    ) -> None:
        if response != "apply":
            return
        self._running = True
        threading.Thread(
            target=self._apply_dnscrypt_worker, args=(server,), daemon=True
        ).start()

    def _apply_dnscrypt_worker(
        self, server: dnscrypt_catalog.DnsCryptServer,
    ) -> None:
        try:
            ok, err = dc.set_servers_blocking([server.id])
        except Exception as e:  # pylint: disable=broad-except
            ok, err = False, f"Excecao: {e}"

        # v0.2.6: poll ate dc.get_status retornar o novo server_names
        # (max 3s). Como em set_global_dns, se nunca aparecer, o
        # expected_active_servers do refresh ja vai marcar a row.
        if ok:
            for _ in range(6):
                try:
                    st = dc.get_status()
                    if server.id in st.server_names:
                        break
                except Exception:  # pylint: disable=broad-except
                    pass
                time.sleep(0.5)
        GLib.idle_add(self._on_apply_dnscrypt_done, ok, err, server)

    def _on_apply_dnscrypt_done(
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
                "Va para a aba Status para verificar.",
            )
            # v0.2.6: idem — passa o server.id como hint pro UI refletir
            # imediatamente mesmo se dc.get_status() ainda nao atualizou.
            self.refresh(expected_active_servers=[server.id])
        return False
