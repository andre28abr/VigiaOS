"""Vigia DNS Manager — gerenciador DNS com UI GTK4.

Foca em systemd-resolved (default no Fedora Silverblue):
- Status dos resolvers atuais
- Catalogo de provedores (Cloudflare, Quad9, AdGuard, Mullvad, ...)
- DNS over TLS (DoT) toggle
- Flush de cache
"""

__version__ = "0.1.0"
__app_id__ = "br.com.vigia.DnsManager"

WRAPPED_PACKAGES = ["systemd-resolved", "resolvectl"]
