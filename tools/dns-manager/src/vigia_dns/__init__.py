"""Vigia DNS Manager — gerenciador DNS focado em privacidade.

v0.3.0 (breaking change): simplificado para usar APENAS dnscrypt-proxy
como backend DNS. As features que existiam dependendo do "modo simples"
(systemd-resolved) foram removidas — dnscrypt-proxy supera em todas:

- DoH (DNS-over-HTTPS), DNSCrypt, DoT
- 11 servers curados (no-logs, DNSSEC, anonymized DNS)
- Blocklist local (Pi-hole-like)
- Estatisticas de queries (24h)
- Migracao 1-click pra/de systemd-resolved padrao

Pre-requisito: dnscrypt-proxy instalado (instale via Vigia Tool Installer
ou `sudo rpm-ostree install dnscrypt-proxy`).

Migracao da v0.2.x: user que estava em "modo simples" ve o botao
"Ativar dnscrypt-proxy" na primeira execucao. Quem ja estava em "modo
avancado" nao precisa fazer nada.
"""

__version__ = "0.3.0"
__app_id__ = "br.com.vigia.DnsManager"

WRAPPED_PACKAGES = ["dnscrypt-proxy"]
