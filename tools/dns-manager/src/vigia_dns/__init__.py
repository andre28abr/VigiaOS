"""Vigia DNS Manager — gerenciador DNS com UI GTK4.

v0.1: foca em systemd-resolved (default no Fedora Silverblue):
- Status dos resolvers atuais
- Catalogo de provedores (Cloudflare, Quad9, AdGuard, Mullvad, ...)
- DNS over TLS (DoT) toggle
- Flush de cache

v0.2: modo avancado opt-in via dnscrypt-proxy (switch no Status):
- Substitui systemd-resolved por dnscrypt-proxy em 127.0.0.1
- DoH (DNS-over-HTTPS), DNSCrypt, anonymized DNS
- Blocklists locais (Pi-hole-like)
- Estatisticas de queries (24h)
- Migracao com backup de resolved.conf + rollback 1-click
"""

__version__ = "0.2.8"
__app_id__ = "br.com.vigia.DnsManager"

WRAPPED_PACKAGES = ["systemd-resolved", "resolvectl", "dnscrypt-proxy"]
