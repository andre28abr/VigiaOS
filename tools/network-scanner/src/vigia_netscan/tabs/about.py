"""Aba Sobre — manual didatico do Vigia Network Scanner."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


SECTIONS: list[tuple[str, str]] = [
    (
        "O que faz",
        "GUI moderna para o <b>nmap</b> — descoberta de hosts (ping scan) "
        "e scan de portas TCP com detecao de servicos. Wrapper para evitar "
        "decorar flags de CLI e parsear output texto. Resultados em UI "
        "navegavel com perfis pre-definidos."
    ),
    (
        "Quando usar",
        "<b>Inventario de rede</b>:\n"
        "Voce trabalha num escritorio e quer saber quais maquinas estao "
        "na rede 192.168.1.0/24. Perfil <i>Discovery</i> resolve em segundos.\n\n"
        "<b>Diagnostico de servico</b>:\n"
        "Servidor de arquivos esta no ar? Perfil <i>Standard</i> com IP do "
        "servidor revela quais portas estao escutando.\n\n"
        "<b>Verificacao de seguranca</b>:\n"
        "Antes de colocar um servidor na rede, escaneie ele mesmo (localhost) "
        "com perfil <i>Full</i> para garantir que so as portas necessarias "
        "estao expostas.\n\n"
        "<b>Auditoria periodica</b>:\n"
        "Para LGPD/compliance: registro periodico de quais servicos estao "
        "expostos. Historico em <tt>~/.local/share/vigia-netscan/</tt> "
        "serve como evidencia."
    ),
    (
        "Uso etico e legal",
        "<b>Scan de redes que voce nao administra e' ilegal</b> em varios "
        "paises, incluindo Brasil (Lei Carolina Dieckmann, art. 154-A do "
        "Codigo Penal — invasao de dispositivo informatico).\n\n"
        "<b>Use apenas em</b>:\n"
        "- Sua propria rede domestica/empresarial\n"
        "- Sistemas para os quais voce tem autorizacao escrita\n"
        "- Targets de CTF (HackTheBox, TryHackMe) e laboratorio\n"
        "- O proprio <tt>scanme.nmap.org</tt>, que existe para testes\n\n"
        "<b>Mesmo dentro de rede propria</b>: scan agressivo pode "
        "tripar IDS/IPS, derrubar dispositivos IoT mal-feitos, ou ativar "
        "alarmes de seguranca da empresa. Avise o admin de rede antes de "
        "perfis intensivos."
    ),
    (
        "Perfis disponiveis",
        "<b>Discovery (ping scan)</b>: so descobre quais hosts respondem. "
        "Mais rapido. Sem port scan.\n\n"
        "<b>Quick</b>: top 100 portas TCP. Rapido. Sem detecao de versao.\n\n"
        "<b>Standard</b>: top 1000 portas + versao de servico (-sV). Default.\n\n"
        "<b>Stealth</b>: SYN scan (-sS). Nao completa handshake. Requer "
        "admin (raw sockets).\n\n"
        "<b>Aggressive</b>: -A (OS detection + version + scripts NSE + "
        "traceroute). Mais informacao. Mais ruido. Requer admin.\n\n"
        "<b>Full</b>: -p- todas as 65535 portas + version. Muito lento "
        "mas exaustivo."
    ),
    (
        "Conceitos importantes",
        "<b>SYN scan vs TCP connect</b>: SYN nao completa handshake (envia "
        "RST apos receber SYN-ACK), historicamente nao aparecia em logs "
        "de aplicacao. TCP connect (default user) completa o handshake e "
        "deixa rastro em <tt>auth.log</tt>/<tt>access.log</tt>.\n\n"
        "<b>CIDR</b>: notacao para subnet. <tt>/24</tt> = 256 IPs (mascara "
        "255.255.255.0). <tt>/16</tt> = 65536 IPs. Cuidado com /16 — "
        "lento e ruidoso.\n\n"
        "<b>Service detection (-sV)</b>: depois de detectar porta aberta, "
        "envia probes especificos para identificar o software (ex: nginx 1.18, "
        "OpenSSH 8.4). Util pra descobrir versoes vulneraveis.\n\n"
        "<b>OS fingerprinting (-O)</b>: analisa quirks da stack TCP/IP para "
        "adivinhar o SO. Mais accurate em hosts proximos (mesmo segmento)."
    ),
    (
        "Resultados e historico",
        "<b>Cada scan e' salvo</b> em <tt>~/.local/share/vigia-netscan/</tt> "
        "como JSON, com mode 0600 (apenas voce le).\n\n"
        "Conteudo: target, perfil usado, timestamp, hosts encontrados, "
        "portas com servico/versao/OS guess.\n\n"
        "Para apagar: <tt>rm ~/.local/share/vigia-netscan/scan-*.json</tt>"
    ),
    (
        "Limitacoes conhecidas",
        "- Sem <b>scripts NSE selecionaveis</b> nesta v0.1. Use perfil "
        "Aggressive para scripts default.\n"
        "- Sem <b>UDP scan</b> (-sU). Demora muito (~10-20 min por host), "
        "raramente util pra desktop.\n"
        "- Sem <b>topologia visual</b> (grafico de hosts). v0.2 alvo.\n"
        "- Sem <b>schedule</b> (cron/systemd timer) via UI.\n"
        "- IPv6 funciona se voce passar IP IPv6 ou hostname com AAAA, "
        "mas perfis usam flags -sV -sS que sao IPv4-default."
    ),
    (
        "Saiba mais",
        "- <tt>man nmap</tt> (capitulos: Discovery, Port Scanning, Service)\n"
        "- Site oficial: https://nmap.org\n"
        "- Livro 'Nmap Network Scanning' por Gordon Lyon (autor do nmap)\n"
        "- Tutorial pratico: https://nmap.org/book/\n"
        "- Scripts NSE: https://nmap.org/nsedoc/\n"
        "- CTFs com nmap: HackTheBox.com, TryHackMe.com"
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
