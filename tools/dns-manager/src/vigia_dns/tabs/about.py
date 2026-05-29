"""Aba Sobre — manual didatico do Vigia DNS Manager."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


SECTIONS: list[tuple[str, str]] = [
    (
        "O que faz",
        "Gerencia o DNS do sistema com <b>dois modos de operação</b>:\n\n"
        "<b>Modo simples (default)</b>: wrappa o <tt>systemd-resolved</tt> "
        "(padrão em Fedora Silverblue). Catálogo curado de 9 provedores "
        "DoT (Cloudflare, Quad9, AdGuard, Mullvad, Google + variantes) "
        "com 1-click para aplicar.\n\n"
        "<b>Modo avançado (v0.2, opt-in)</b>: substitui o systemd-resolved "
        "por <tt>dnscrypt-proxy</tt> em <tt>127.0.0.1:53</tt>. Habilita:\n"
        "• DoH (DNS-over-HTTPS, porta 443 — passa por censura/inspeção)\n"
        "• Blocklists locais (Pi-hole-like — bloquear ads/tracking)\n"
        "• Anonymized DNS (relays escondem seu IP do resolver final)\n"
        "• Estatísticas de queries (24h)\n"
        "• DNSSEC validation explícito\n\n"
        "Toggle pelo switch <i>Ativar modo avançado</i> no rodapé da aba "
        "Status. Migração com backup automático do <tt>resolved.conf</tt> "
        "e rollback 1-click."
    ),
    (
        "Modo avançado: por que usar",
        "<b>Casos de uso (escritório LGPD)</b>:\n\n"
        "• Bloquear domínios de tracking corporate (DoubleClick, "
        "GoogleTagManager, Facebook Pixel, etc.) em toda a rede do "
        "escritório sem instalar Pi-hole em hardware separado.\n\n"
        "• Forçar DNSSEC validation explícito — garante que ninguém "
        "está interceptando ou modificando respostas DNS no caminho.\n\n"
        "• Usar Anonymized DNS — o resolver final não vê seu IP, vê "
        "apenas o IP do relay (similar a Tor, mas só para DNS).\n\n"
        "• Auditar queries do sistema — saber quais domínios foram "
        "consultados nas últimas 24h (útil para identificar apps "
        "fofoqueiros ou exfiltração).\n\n"
        "<b>Quando NÃO usar</b>:\n"
        "• Setup home casual onde systemd-resolved + DoT já basta\n"
        "• Sistemas que dependem de DNS-from-DHCP automático (a config "
        "do dnscrypt é estática — você escolhe quais servers)\n"
        "• Ambientes com proxy corporate que intercepta DNS no firewall"
    ),
    (
        "Como usar",
        "<b>1. Ver o que está em uso</b>:\n"
        "Aba <i>Status</i> mostra:\n"
        "- Hero card com nome do provedor (se detectado)\n"
        "- DNS configurado (global + por interface)\n"
        "- DoT habilitado ou não\n"
        "- Estado do systemd-resolved\n\n"
        "<b>2. Trocar de provedor</b>:\n"
        "1. Aba <i>Provedores</i>\n"
        "2. Veja a descrição + filtros de cada um (ads, malware, etc.)\n"
        "3. Switch <i>DNS over TLS</i> no topo (recomendado ON)\n"
        "4. Clique <i>Aplicar</i> no provedor desejado\n"
        "5. Confirma o dialog\n"
        "6. Polkit pede senha\n"
        "7. Backup do config atual é salvo em .vigia-backup\n"
        "8. systemd-resolved reinicia automaticamente\n\n"
        "<b>3. Limpar cache</b>:\n"
        "Aba <i>Status</i> > <i>Limpar cache DNS</i>. Útil quando você "
        "muda DNS e quer forçar nova resolução (sem esperar TTL expirar).\n\n"
        "<b>4. Voltar atrás</b>:\n"
        "Aba <i>Status</i> > <i>Restaurar padrão</i>. Restaura o backup "
        ".vigia-backup criado na primeira aplicação."
    ),
    (
        "Conceitos importantes",
        "<b>DNS</b> = traduz nomes (google.com) em IPs (172.217.x.x). "
        "Por padrão, queries vão em <i>plaintext UDP/53</i> — qualquer um "
        "no caminho vê seu histórico de navegação.\n\n"
        "<b>DNS over TLS (DoT)</b> = mesma resolução mas via TLS na porta "
        "853. ISP não consegue ver. systemd-resolved suporta nativamente.\n\n"
        "<b>DNS over HTTPS (DoH)</b> = via HTTPS porta 443. Indistinguível "
        "de tráfego web normal. Suportado pelo navegador (Firefox/Chrome) "
        "ou via dnscrypt-proxy. systemd-resolved não suporta nativamente.\n\n"
        "<b>Resolver com filtros</b> = AdGuard/Cloudflare Family/Quad9 etc. "
        "Bloqueiam domínios maliciosos OU ads OU adultos no nível DNS — "
        "antes do navegador nem requisitar. Mais leve que ad-blocker no "
        "browser e funciona em todos os apps.\n\n"
        "<b>systemd-resolved</b> = daemon padrão do systemd para DNS. "
        "Lê <tt>/etc/systemd/resolved.conf</tt> e responde queries via stub "
        "em 127.0.0.53. NetworkManager geralmente fornece DNS por interface "
        "que sobrescreve o global do .conf — verifique aba Status."
    ),
    (
        "Limitações conhecidas",
        "- DoT funciona, <b>DoH não</b> (systemd-resolved não suporta DoH "
        "nativamente). Para DoH, precisaria de dnscrypt-proxy em paralelo.\n"
        "- Blocklists tipo Pi-hole não estão na v0.1. Para isso, use "
        "<i>AdGuard DNS</i> ou <i>Mullvad AdBlock</i> que já filtram no "
        "lado do servidor.\n"
        "- NetworkManager pode sobrescrever o DNS por interface ao "
        "reconectar Wi-Fi. Para forçar uso do global, edite a conexão em "
        "<tt>nmcli</tt> com <tt>ignore-auto-dns yes</tt>.\n"
        "- Mullvad DNS só funciona via DoT/DoH (sem plaintext). Se DoT "
        "estiver OFF, queries pra Mullvad vão falhar."
    ),
    (
        "Saiba mais",
        "- <tt>man systemd-resolved.service</tt>\n"
        "- <tt>man resolvectl</tt>\n"
        "- <tt>man systemd-resolved.conf</tt>\n"
        "- <tt>resolvectl status</tt> — comando para inspecionar manualmente\n"
        "- DNS leak test: https://dnsleaktest.com\n"
        "- Comparativo de DNS publicos: https://www.dnsperf.com/"
    ),
]


class AboutTab(Adw.Bin):
    def __init__(self) -> None:
        super().__init__()
        page = Adw.PreferencesPage()
        for title, content in SECTIONS:
            group = Adw.PreferencesGroup()
            group.set_title(title)
            label = Gtk.Label()
            label.set_markup(content)
            label.set_wrap(True)
            label.set_xalign(0)
            label.set_selectable(True)
            label.set_margin_start(12)
            label.set_margin_end(12)
            label.set_margin_top(12)
            label.set_margin_bottom(12)
            row = Adw.PreferencesRow()
            row.set_child(label)
            row.set_activatable(False)
            group.add(row)
            page.add(group)
        self.set_child(page)
