"""Vigia DNS Manager — DNS encriptado via dnscrypt-proxy.

v0.4.0: enxugado. 3 tabs (Status, Provedores, Sobre).

Por que enxugar (v0.3 -> v0.4):
- Blocklist DNS local quebra layout (browser deixa buraco no lugar do ad).
  Extensoes de navegador (uBlock Origin) fazem ad-blocking MUITO melhor:
  esconde elemento, anti-anti-adblock, whitelist por site, etc.
- Stats de queries dependiam de query log habilitado, que ja eh
  decisao de privacidade complexa. Sem stats, sem precisar dessa
  feature opcional.
- Foco: DNS encriptado (DoH/DoT/DNSCrypt) com servers curados.
  Extensoes de navegador (catalogo no Vigia Tool Installer) cuidam
  do bloqueio de ads/trackers no nivel certo.

Pre-requisito: dnscrypt-proxy instalado.
"""

__version__ = "0.4.3"
__app_id__ = "br.com.vigia.DnsManager"

WRAPPED_PACKAGES = ["dnscrypt-proxy"]
