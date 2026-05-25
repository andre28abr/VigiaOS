"""Wrapper interno para evitar conflito de nome entre o modulo `resolvers.py`
(catalogo) e a tab `tabs/resolvers.py`.

Exporta as funcoes necessarias da Catalog.
"""

from .resolvers import CATALOG, DnsResolver, find_by_id, find_by_server


def find_resolver_for_servers(servers: list[str]) -> DnsResolver | None:
    """Se qualquer IP da lista bater com um resolver conhecido, retorna ele."""
    for srv in servers:
        r = find_by_server(srv)
        if r is not None:
            return r
    return None


__all__ = ["CATALOG", "DnsResolver", "find_by_id", "find_by_server", "find_resolver_for_servers"]
