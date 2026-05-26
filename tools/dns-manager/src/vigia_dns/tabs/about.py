"""Aba Sobre — manual didatico do Vigia DNS Manager."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


SECTIONS: list[tuple[str, str]] = [
    (
        "O que faz",
        "Gerencia o DNS do sistema com <b>dois modos de operacao</b>:\n\n"
        "<b>Modo simples (default)</b>: wrappa o <tt>systemd-resolved</tt> "
        "(padrao em Fedora Silverblue). Catalogo curado de 9 provedores "
        "DoT (Cloudflare, Quad9, AdGuard, Mullvad, Google + variantes) "
        "com 1-click para aplicar.\n\n"
        "<b>Modo avancado (v0.2, opt-in)</b>: substitui o systemd-resolved "
        "por <tt>dnscrypt-proxy</tt> em <tt>127.0.0.1:53</tt>. Habilita:\n"
        "• DoH (DNS-over-HTTPS, porta 443 — passa por censura/inspecao)\n"
        "• Blocklists locais (Pi-hole-like — bloquear ads/tracking)\n"
        "• Anonymized DNS (relays escondem seu IP do resolver final)\n"
        "• Estatisticas de queries (24h)\n"
        "• DNSSEC validation explicito\n\n"
        "Toggle pelo switch <i>Ativar modo avancado</i> no rodape da aba "
        "Status. Migracao com backup automatico do <tt>resolved.conf</tt> "
        "e rollback 1-click."
    ),
    (
        "Modo avancado: por que usar",
        "<b>Casos de uso (escritorio LGPD)</b>:\n\n"
        "• Bloquear dominios de tracking corporate (DoubleClick, "
        "GoogleTagManager, Facebook Pixel, etc.) em toda a rede do "
        "escritorio sem instalar Pi-hole em hardware separado.\n\n"
        "• Forcar DNSSEC validation explicito — garante que ninguem "
        "esta interceptando ou modificando respostas DNS no caminho.\n\n"
        "• Usar Anonymized DNS — o resolver final nao ve seu IP, ve "
        "apenas o IP do relay (similar a Tor, mas so para DNS).\n\n"
        "• Auditar queries do sistema — saber quais dominios foram "
        "consultados nas ultimas 24h (util para identificar apps "
        "fofoqueiros ou exfiltracao).\n\n"
        "<b>Quando NAO usar</b>:\n"
        "• Setup home casual onde systemd-resolved + DoT ja basta\n"
        "• Sistemas que dependem de DNS-from-DHCP automatico (a config "
        "do dnscrypt e' estatica — voce escolhe quais servers)\n"
        "• Ambientes com proxy corporate que intercepta DNS no firewall"
    ),
    (
        "Como usar",
        "<b>1. Ver o que esta em uso</b>:\n"
        "Aba <i>Status</i> mostra:\n"
        "- Hero card com nome do provedor (se detectado)\n"
        "- DNS configurado (global + por interface)\n"
        "- DoT habilitado ou nao\n"
        "- Estado do systemd-resolved\n\n"
        "<b>2. Trocar de provedor</b>:\n"
        "1. Aba <i>Provedores</i>\n"
        "2. Veja a descricao + filtros de cada um (ads, malware, etc.)\n"
        "3. Switch <i>DNS over TLS</i> no topo (recomendado ON)\n"
        "4. Clique <i>Aplicar</i> no provedor desejado\n"
        "5. Confirma o dialog\n"
        "6. Polkit pede senha\n"
        "7. Backup do config atual e' salvo em .vigia-backup\n"
        "8. systemd-resolved reinicia automaticamente\n\n"
        "<b>3. Limpar cache</b>:\n"
        "Aba <i>Status</i> > <i>Limpar cache DNS</i>. Util quando voce "
        "muda DNS e quer forcar nova resolucao (sem esperar TTL expirar).\n\n"
        "<b>4. Voltar atras</b>:\n"
        "Aba <i>Status</i> > <i>Restaurar padrao</i>. Restaura o backup "
        ".vigia-backup criado na primeira aplicacao."
    ),
    (
        "Conceitos importantes",
        "<b>DNS</b> = traduz nomes (google.com) em IPs (172.217.x.x). "
        "Por padrao, queries vao em <i>plaintext UDP/53</i> — qualquer um "
        "no caminho ve seu historico de navegacao.\n\n"
        "<b>DNS over TLS (DoT)</b> = mesma resolucao mas via TLS na porta "
        "853. ISP nao consegue ver. systemd-resolved suporta nativamente.\n\n"
        "<b>DNS over HTTPS (DoH)</b> = via HTTPS porta 443. Indistinguivel "
        "de trafego web normal. Suportado pelo navegador (Firefox/Chrome) "
        "ou via dnscrypt-proxy. systemd-resolved nao suporta nativamente.\n\n"
        "<b>Resolver com filtros</b> = AdGuard/Cloudflare Family/Quad9 etc. "
        "Bloqueiam dominios maliciosos OU ads OU adultos no nivel DNS — "
        "antes do navegador nem requisitar. Mais leve que ad-blocker no "
        "browser e funciona em todos os apps.\n\n"
        "<b>systemd-resolved</b> = daemon padrao do systemd para DNS. "
        "Le <tt>/etc/systemd/resolved.conf</tt> e responde queries via stub "
        "em 127.0.0.53. NetworkManager geralmente fornece DNS por interface "
        "que sobrescreve o global do .conf — verifique aba Status."
    ),
    (
        "Limitacoes conhecidas",
        "- DoT funciona, <b>DoH nao</b> (systemd-resolved nao suporta DoH "
        "nativamente). Para DoH, precisaria de dnscrypt-proxy em paralelo.\n"
        "- Blocklists tipo Pi-hole nao estao na v0.1. Para isso, use "
        "<i>AdGuard DNS</i> ou <i>Mullvad AdBlock</i> que ja filtram no "
        "lado do servidor.\n"
        "- NetworkManager pode sobrescrever o DNS por interface ao "
        "reconectar Wi-Fi. Para forcar uso do global, edite a conexao em "
        "<tt>nmcli</tt> com <tt>ignore-auto-dns yes</tt>.\n"
        "- Mullvad DNS so funciona via DoT/DoH (sem plaintext). Se DoT "
        "estiver OFF, queries pra Mullvad vao falhar."
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
