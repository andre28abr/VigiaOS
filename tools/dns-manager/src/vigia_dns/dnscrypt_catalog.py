"""Catalogo de servers dnscrypt-proxy curados.

Nomes oficiais sao das public-resolvers.md do upstream:
https://github.com/DNSCrypt/dnscrypt-resolvers

Curadoria Vigia: providers com boas politicas de privacy, sem logging
publicamente verificavel, e ampla cobertura geografica (BR inclusive).

Estes nomes vao no `server_names = [...]` do dnscrypt-proxy.toml.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DnsCryptServer:
    id: str                   # nome canonico no public-resolvers.md
    label: str                # nome amigavel para UI
    provider: str             # ex: "Cloudflare", "Quad9"
    protocol: str             # "DoH", "DoT", "DNSCrypt"
    no_logs: bool             # claim do provider (verificavel?)
    no_filter: bool           # nao bloqueia dominios
    dnssec: bool              # valida DNSSEC
    description: str
    country: str = ""         # ISO country code do operador (BR, US, CH, ...)


# Lista curada — subset dos ~200 servers do public-resolvers.md
SERVERS: list[DnsCryptServer] = [
    # === Cloudflare ===
    DnsCryptServer(
        id="cloudflare",
        label="Cloudflare (DoH)",
        provider="Cloudflare",
        protocol="DoH",
        no_logs=True,
        no_filter=True,
        dnssec=True,
        description=(
            "Resolver oficial 1.1.1.1 via DNS-over-HTTPS. Sem filtros, "
            "sem logs persistentes. Boa performance no Brasil (POP SP)."
        ),
        country="US",
    ),
    DnsCryptServer(
        id="cloudflare-security",
        label="Cloudflare Security (DoH)",
        provider="Cloudflare",
        protocol="DoH",
        no_logs=True,
        no_filter=False,
        dnssec=True,
        description=(
            "Cloudflare 1.1.1.2 — bloqueia malware/phishing conhecidos. "
            "Variante de segurança do 1.1.1.1."
        ),
        country="US",
    ),
    DnsCryptServer(
        id="cloudflare-family",
        label="Cloudflare Family (DoH)",
        provider="Cloudflare",
        protocol="DoH",
        no_logs=True,
        no_filter=False,
        dnssec=True,
        description=(
            "Cloudflare 1.1.1.3 — bloqueia malware + conteúdo adulto. "
            "Recomendado para ambiente familiar."
        ),
        country="US",
    ),

    # === Quad9 ===
    DnsCryptServer(
        id="quad9-doh-ip4-port443-filter-pri",
        label="Quad9 (DoH, filtrado)",
        provider="Quad9",
        protocol="DoH",
        no_logs=True,
        no_filter=False,
        dnssec=True,
        description=(
            "Quad9 9.9.9.9 — bloqueia domínios maliciosos (threat "
            "intelligence). Suíça, sem fins lucrativos."
        ),
        country="CH",
    ),
    DnsCryptServer(
        id="quad9-doh-ip4-nofilter-pri",
        label="Quad9 (DoH, sem filtro)",
        provider="Quad9",
        protocol="DoH",
        no_logs=True,
        no_filter=True,
        dnssec=True,
        description=(
            "Quad9 9.9.9.10 — variante sem filtros. Para quem prefere "
            "controlar filtros via blocklist própria."
        ),
        country="CH",
    ),

    # === AdGuard ===
    DnsCryptServer(
        id="adguard-dns-doh",
        label="AdGuard DNS (DoH)",
        provider="AdGuard",
        protocol="DoH",
        no_logs=True,
        no_filter=False,
        dnssec=True,
        description=(
            "Bloqueia ads + trackers + malware. Útil para reduzir "
            "tracking de marketing em escritório."
        ),
        country="CY",
    ),
    DnsCryptServer(
        id="adguard-dns-family-doh",
        label="AdGuard Family (DoH)",
        provider="AdGuard",
        protocol="DoH",
        no_logs=True,
        no_filter=False,
        dnssec=True,
        description=(
            "AdGuard com bloqueio adicional de conteúdo adulto. "
            "Variante mais restritiva."
        ),
        country="CY",
    ),

    # === Mullvad ===
    DnsCryptServer(
        id="mullvad-doh",
        label="Mullvad DNS (DoH)",
        provider="Mullvad",
        protocol="DoH",
        no_logs=True,
        no_filter=True,
        dnssec=True,
        description=(
            "Operado pela Mullvad VPN (Suécia). Política de privacy "
            "verificável, sem filtros."
        ),
        country="SE",
    ),
    DnsCryptServer(
        id="mullvad-adblock-doh",
        label="Mullvad Adblock (DoH)",
        provider="Mullvad",
        protocol="DoH",
        no_logs=True,
        no_filter=False,
        dnssec=True,
        description=(
            "Mullvad com bloqueio de ads + trackers. Mesmo backbone "
            "mas com filtros."
        ),
        country="SE",
    ),

    # === DNSCrypt-protocol (alternativa nao-HTTP) ===
    DnsCryptServer(
        id="dnscrypt-quad9",
        label="Quad9 (DNSCrypt)",
        provider="Quad9",
        protocol="DNSCrypt",
        no_logs=True,
        no_filter=False,
        dnssec=True,
        description=(
            "Quad9 via protocolo DNSCrypt (alternativa ao DoH). "
            "Útil em redes que bloqueiam HTTPS/DoH."
        ),
        country="CH",
    ),

    # === Anonymized DNS relay (esconde IP do user) ===
    # Notas: usar com `anonymized_dns` config — relay esconde IP do user
    # do resolver final. Para v0.2.0 listamos mas o setup requer config
    # extra (proxy = ["anon-cs-fr"]).
    DnsCryptServer(
        id="anon-cs-fr",
        label="Anonymized DNS Relay (FR)",
        provider="Anonymized DNS",
        protocol="DNSCrypt",
        no_logs=True,
        no_filter=True,
        dnssec=True,
        description=(
            "Relay localizado na França para anonymized DNS. Usado em "
            "conjunto com outro server — esconde seu IP do resolver "
            "final. Setup mais complexo (v0.2.1+)."
        ),
        country="FR",
    ),
]


def find_by_id(server_id: str) -> DnsCryptServer | None:
    for s in SERVERS:
        if s.id == server_id:
            return s
    return None


def list_by_provider(provider: str) -> list[DnsCryptServer]:
    return [s for s in SERVERS if s.provider == provider]


def providers() -> list[str]:
    """Lista de providers unicos (ordem alfabetica)."""
    return sorted(set(s.provider for s in SERVERS))


def default_servers() -> list[str]:
    """Servers default — Cloudflare DoH (rapido, sem filtros) como primeiro."""
    return ["cloudflare", "quad9-doh-ip4-port443-filter-pri"]
