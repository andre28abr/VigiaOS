"""Aba Sobre — manual didatico do Vigia DNS Manager."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


SECTIONS: list[tuple[str, str]] = [
    (
        "O que faz",
        "Coloca o <b>dnscrypt-proxy</b> como resolvedor DNS da máquina e "
        "cuida de toda a configuração por você. Em vez do DNS em texto "
        "puro (UDP/53) que o Fedora usa por padrão via "
        "<tt>systemd-resolved</tt>, as consultas passam a sair "
        "<b>encriptadas</b> — por <b>DoH</b> (DNS-over-HTTPS, porta 443) "
        "ou pelo protocolo <b>DNSCrypt</b>.\n\n"
        "<b>Catálogo curado de 11 servers</b> (Cloudflare, Quad9, AdGuard, "
        "Mullvad + variantes com filtro) com descrição, país e selos "
        "(DoH/DNSCrypt, sem logs, DNSSEC, sem filtro). Aplicar é 1 clique: "
        "a tool edita o <tt>dnscrypt-proxy.toml</tt> e reinicia o serviço.\n\n"
        "<b>Migração com volta garantida</b>: ao ativar, faz backup do "
        "<tt>resolved.conf</tt> e do <tt>resolv.conf</tt>, desliga o "
        "systemd-resolved e aponta o sistema para <tt>127.0.0.1</tt>. O "
        "botão <i>Restaurar systemd-resolved</i> desfaz tudo."
    ),
    (
        "Por que usar (escritório LGPD)",
        "• Por padrão, <b>qualquer um no caminho</b> (provedor, Wi-Fi do "
        "café, roteador comprometido) vê cada domínio que você consulta. "
        "Com DoH/DNSCrypt, vê só tráfego cifrado.\n\n"
        "• <b>Filtro no nível DNS</b>: AdGuard, Mullvad AdBlock, Cloudflare "
        "Security/Family e Quad9 bloqueiam malware, tracking ou conteúdo "
        "adulto antes de o navegador nem requisitar — vale para todos os "
        "apps, não só o browser.\n\n"
        "• <b>DNSSEC</b> e <b>no-logs</b> exigíveis: o dnscrypt-proxy pode "
        "recusar servers que não validam respostas ou que registram "
        "consultas (a aba Status mostra se estão exigidos).\n\n"
        "<b>Quando NÃO usar</b>:\n"
        "• Redes que dependem do DNS entregue por DHCP (rede corporativa "
        "com nomes internos) — a configuração do dnscrypt é estática\n"
        "• Ambientes com proxy corporativo que intercepta DNS no firewall"
    ),
    (
        "Como usar",
        "<b>1. Instalar o dnscrypt-proxy</b> (uma vez): pelo Tool Installer "
        "ou <tt>sudo dnf install dnscrypt-proxy</tt>. A aba <i>Status</i> "
        "avisa se está faltando.\n\n"
        "<b>2. Ativar</b>: aba <i>Status</i> > <i>Ativar dnscrypt-proxy</i>. "
        "Confirma o diálogo, Polkit pede a senha, e UMA chamada faz tudo: "
        "backups, para o systemd-resolved, reescreve o "
        "<tt>/etc/resolv.conf</tt> e liga o serviço. O hero passa a "
        "<i>Ativo e seguro</i>.\n\n"
        "<b>3. Escolher o server</b>: aba <i>Provedores</i>, leia a "
        "descrição e os selos, clique <i>Aplicar</i>. Backup do "
        "<tt>.toml</tt> em <tt>.vigia-backup</tt>, serviço reinicia sozinho. "
        "O botão vira <i>Em uso</i>.\n\n"
        "<b>4. Conferir</b>: aba <i>Status</i> mostra serviço, versão, "
        "endereço de escuta, servers ativos e se DNSSEC/no-logs estão "
        "exigidos. <i>Atualizar</i> relê tudo.\n\n"
        "<b>5. Voltar atrás</b>: <i>Restaurar systemd-resolved</i> restaura "
        "os backups e religa o padrão do Fedora."
    ),
    (
        "Conceitos importantes",
        "<b>DNS</b> = traduz nomes (google.com) em IPs (172.217.x.x). "
        "Por padrão, as consultas vão em <i>texto puro na porta 53</i> — "
        "qualquer um no caminho vê seu histórico de navegação.\n\n"
        "<b>DNS over HTTPS (DoH)</b> = a mesma resolução, mas dentro de "
        "HTTPS na porta 443. Indistinguível de tráfego web normal — passa "
        "por redes que bloqueiam portas. É o protocolo da maioria dos "
        "servers do catálogo.\n\n"
        "<b>DNSCrypt</b> = protocolo próprio, mais antigo que o DoH, com "
        "autenticação do server por chave pública. Alternativa quando "
        "HTTPS está bloqueado ou inspecionado (ex.: <i>Quad9 (DNSCrypt)</i>)."
        "\n\n"
        "<b>dnscrypt-proxy</b> = o programa que fala esses protocolos. Roda "
        "local em <tt>127.0.0.1:53</tt>, recebe as consultas do sistema e "
        "repassa cifradas ao server escolhido. Config em "
        "<tt>/etc/dnscrypt-proxy/dnscrypt-proxy.toml</tt> — a tool edita "
        "linha a linha, preservando seus comentários.\n\n"
        "<b>Anonymized DNS</b> = um <i>relay</i> intermediário (ex.: "
        "<i>anon-cs-fr</i>) esconde seu IP do resolvedor final — parecido "
        "com Tor, só que para DNS."
    ),
    (
        "Limitações conhecidas",
        "- Requer o pacote <tt>dnscrypt-proxy</tt> instalado; a tool não o "
        "instala sozinha (use o Tool Installer).\n"
        "- A configuração é <b>estática</b>: o DNS entregue por DHCP é "
        "ignorado enquanto o dnscrypt-proxy estiver ativo.\n"
        "- O <i>Anonymized DNS Relay</i> aparece no catálogo, mas para "
        "funcionar precisa de configuração extra de <tt>anonymized_dns</tt> "
        "no <tt>.toml</tt> — a tool ainda não faz isso.\n"
        "- Sem blocklists locais nem estatísticas de consultas (removidas "
        "na v0.4 — bloqueio de ads é melhor servido por uBlock Origin no "
        "navegador ou por um server com filtro).\n"
        "- NetworkManager pode reescrever <tt>/etc/resolv.conf</tt> ao "
        "reconectar o Wi-Fi. Para forçar, edite a conexão em "
        "<tt>nmcli</tt> com <tt>ignore-auto-dns yes</tt>.\n"
        "- Editar o <tt>.toml</tt> à mão enquanto a tool está aberta pode "
        "confundir a leitura (a edição é por linha, não reserializa o "
        "arquivo)."
    ),
    (
        "Saiba mais",
        "- <tt>man dnscrypt-proxy</tt> e "
        "https://github.com/DNSCrypt/dnscrypt-proxy/wiki\n"
        "- Lista oficial de servers: "
        "https://github.com/DNSCrypt/dnscrypt-resolvers\n"
        "- <tt>systemctl status dnscrypt-proxy</tt> — inspecionar o serviço\n"
        "- <tt>cat /etc/resolv.conf</tt> — deve apontar para 127.0.0.1\n"
        "- DNS leak test: https://dnsleaktest.com\n"
        "- Comparativo de DNS públicos: https://www.dnsperf.com/"
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
