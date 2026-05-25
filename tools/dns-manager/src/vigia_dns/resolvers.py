"""Catalogo curado de DNS resolvers populares."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DnsResolver:
    id: str              # ex: "cloudflare"
    name: str            # ex: "Cloudflare"
    description: str     # 1 linha
    why: str             # paragrafo: posicionamento, privacidade, filtros
    servers_v4: list[str] = field(default_factory=list)
    servers_v6: list[str] = field(default_factory=list)
    supports_dot: bool = False    # DNS over TLS
    supports_doh: bool = False    # DNS over HTTPS
    dot_hostname: str = ""        # ex: "cloudflare-dns.com" (para verificacao de cert)
    filters: list[str] = field(default_factory=list)  # ex: ["malware", "ads"]


CATALOG: list[DnsResolver] = [
    DnsResolver(
        id="cloudflare",
        name="Cloudflare",
        description="DNS rapido com foco em privacidade (no-logs).",
        why=(
            "DNS publico mais rapido em benchmarks globais (~10ms na maioria "
            "dos lugares). Cloudflare declara nao logar IPs e auditoria por "
            "KPMG. Suporta DoT e DoH."
        ),
        servers_v4=["1.1.1.1", "1.0.0.1"],
        servers_v6=["2606:4700:4700::1111", "2606:4700:4700::1001"],
        supports_dot=True,
        supports_doh=True,
        dot_hostname="cloudflare-dns.com",
        filters=[],
    ),
    DnsResolver(
        id="cloudflare-malware",
        name="Cloudflare Malware",
        description="Cloudflare com filtro de malware.",
        why=(
            "Cloudflare 1.1.1.2 bloqueia dominios sabidamente maliciosos "
            "(ransomware C2, phishing). Mantem a velocidade do Cloudflare "
            "regular mas adiciona uma camada de protecao."
        ),
        servers_v4=["1.1.1.2", "1.0.0.2"],
        servers_v6=["2606:4700:4700::1112", "2606:4700:4700::1002"],
        supports_dot=True,
        supports_doh=True,
        dot_hostname="security.cloudflare-dns.com",
        filters=["malware"],
    ),
    DnsResolver(
        id="cloudflare-family",
        name="Cloudflare Family",
        description="Cloudflare com filtro de malware + conteudo adulto.",
        why=(
            "Cloudflare 1.1.1.3 = bloqueio de malware + bloqueio de "
            "conteudo adulto. Util em redes com criancas (escritorio "
            "compartilhado, casa)."
        ),
        servers_v4=["1.1.1.3", "1.0.0.3"],
        servers_v6=["2606:4700:4700::1113", "2606:4700:4700::1003"],
        supports_dot=True,
        supports_doh=True,
        dot_hostname="family.cloudflare-dns.com",
        filters=["malware", "adult"],
    ),
    DnsResolver(
        id="quad9",
        name="Quad9",
        description="DNS com foco em seguranca (bloqueia maliciosos).",
        why=(
            "Mantido por uma organizacao sem fins lucrativos (Suica). "
            "Bloqueia dominios maliciosos via feeds de inteligencia "
            "de seguranca (IBM, Anti-Phishing Working Group, etc.). "
            "Privacidade boa: sem PII logada."
        ),
        servers_v4=["9.9.9.9", "149.112.112.112"],
        servers_v6=["2620:fe::fe", "2620:fe::9"],
        supports_dot=True,
        supports_doh=True,
        dot_hostname="dns.quad9.net",
        filters=["malware"],
    ),
    DnsResolver(
        id="adguard",
        name="AdGuard DNS",
        description="DNS publico que bloqueia ads e trackers.",
        why=(
            "Bloqueia centenas de milhares de servidores de ads, trackers "
            "e analytics no nivel DNS — antes do navegador nem requisitar. "
            "Reduz banda, melhora privacidade. Sem fins lucrativos."
        ),
        servers_v4=["94.140.14.14", "94.140.15.15"],
        servers_v6=["2a10:50c0::ad1:ff", "2a10:50c0::ad2:ff"],
        supports_dot=True,
        supports_doh=True,
        dot_hostname="dns.adguard-dns.com",
        filters=["ads", "trackers"],
    ),
    DnsResolver(
        id="adguard-family",
        name="AdGuard Family",
        description="AdGuard + bloqueio de conteudo adulto.",
        why=(
            "AdGuard com adicao de filtros parentais. Ideal para escritorio "
            "compartilhado ou rede domestica com criancas."
        ),
        servers_v4=["94.140.14.15", "94.140.15.16"],
        servers_v6=["2a10:50c0::bad1:ff", "2a10:50c0::bad2:ff"],
        supports_dot=True,
        supports_doh=True,
        dot_hostname="family.adguard-dns.com",
        filters=["ads", "trackers", "adult"],
    ),
    DnsResolver(
        id="mullvad",
        name="Mullvad DNS",
        description="DNS publico da Mullvad (no-logs estrito).",
        why=(
            "Mullvad e' provedor sueco com forte foco em privacidade. "
            "DNS publico desde 2023. So funciona via DoT/DoH — sem "
            "plaintext UDP/53. Sem logs."
        ),
        servers_v4=["194.242.2.2", "194.242.2.3"],
        servers_v6=["2a07:e340::2", "2a07:e340::3"],
        supports_dot=True,
        supports_doh=True,
        dot_hostname="base.dns.mullvad.net",
        filters=[],
    ),
    DnsResolver(
        id="mullvad-adblock",
        name="Mullvad AdBlock",
        description="Mullvad DNS + bloqueio de ads/trackers/malware.",
        why=(
            "Mesma confiabilidade da Mullvad com bloqueio agressivo de "
            "ads e trackers. Combina privacidade e bloqueio em um so "
            "resolver."
        ),
        servers_v4=["194.242.2.3", "194.242.2.4"],
        servers_v6=["2a07:e340::3", "2a07:e340::4"],
        supports_dot=True,
        supports_doh=True,
        dot_hostname="adblock.dns.mullvad.net",
        filters=["ads", "trackers", "malware"],
    ),
    DnsResolver(
        id="google",
        name="Google Public DNS",
        description="DNS publico do Google (rapido, mas Google ve queries).",
        why=(
            "Rapido e estavel mas Google logga IPs por ate 48h e "
            "queries amostradas para 'melhoria do servico'. Use se prioriza "
            "velocidade sobre privacidade."
        ),
        servers_v4=["8.8.8.8", "8.8.4.4"],
        servers_v6=["2001:4860:4860::8888", "2001:4860:4860::8844"],
        supports_dot=True,
        supports_doh=True,
        dot_hostname="dns.google",
        filters=[],
    ),
]


def find_by_id(resolver_id: str) -> DnsResolver | None:
    for r in CATALOG:
        if r.id == resolver_id:
            return r
    return None


def find_by_server(server: str) -> DnsResolver | None:
    """Identifica resolver pelo IP. Util pra detectar o em uso atualmente."""
    for r in CATALOG:
        if server in r.servers_v4 or server in r.servers_v6:
            return r
    return None
