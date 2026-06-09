"""Tab Escutando: o que do SEU PC está aberto pra rede (servidores ativos),
com um glossário explicando o que é cada porta.

Subclasse de ConnectionsTab — reusa a máquina de refresh/admin, mas troca os
hooks de fetch/summary/render.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .. import backend, humanize
from .connections import ConnectionsTab


class ListeningTab(ConnectionsTab):
    """Servidores ativos no host (LISTEN / UDP UNCONN), explicados."""

    _show_hide_local = False  # tudo aqui é local por natureza

    def _fetch(self) -> list[backend.NetConnection]:
        return backend.list_listening(elevated=self._elevated_mode)

    def _summary_text(self, conns: list[backend.NetConnection]) -> str:
        n = len(conns)
        return (f"{n} porta{'s' if n != 1 else ''} escutando "
                "(programas do seu PC abertos pra rede)")

    @staticmethod
    def _port_num(c: backend.NetConnection) -> int:
        _host, port = humanize.split_host_port(c.local_addr)
        try:
            return int(port)
        except (TypeError, ValueError):
            return 999999

    def _render_into(self, conns: list[backend.NetConnection]) -> None:
        for c in sorted(conns, key=self._port_num):
            host, port = humanize.split_host_port(c.local_addr)
            hint = humanize.port_hint(port)
            proc = c.process if c.process != "?" else "(app do sistema)"

            row = Adw.ActionRow()
            row.set_title(f"Porta {port}" + (f" — {hint}" if hint else ""))
            if host in ("0.0.0.0", "::", "*"):
                scope = "aberta pra qualquer rede"
            elif humanize.is_loopback(c.local_addr):
                scope = "só neste PC (local)"
            else:
                scope = host
            row.set_subtitle(f"{proc} · {c.proto.upper()} · {scope}")
            row.add_prefix(Gtk.Image.new_from_icon_name("network-server-symbolic"))

            # destaque suave: portas abertas pra qualquer rede pedem mais atenção
            if host in ("0.0.0.0", "::", "*"):
                tag = Gtk.Label(label="exposta")
                tag.add_css_class("warning")
                tag.add_css_class("caption")
                tag.set_valign(Gtk.Align.CENTER)
                row.add_suffix(tag)

            self._list.append(row)
            self._row_search_text[row] = (
                f"{port} {hint} {proc} {c.proto} {scope}").lower()
