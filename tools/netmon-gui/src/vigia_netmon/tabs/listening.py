"""Tab Listening: so sockets em LISTEN / UNCONN com wildcard peer.

Subclass de ConnectionsTab que so muda a query do backend.
"""

from __future__ import annotations

from .. import backend
from .connections import ConnectionsTab


class ListeningTab(ConnectionsTab):
    """Mostra apenas servidores ativos no host (LISTEN ou UDP UNCONN)."""

    def _fetch(self) -> list[backend.NetConnection]:
        return backend.list_listening()
