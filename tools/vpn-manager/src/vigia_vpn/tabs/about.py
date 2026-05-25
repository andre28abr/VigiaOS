"""Aba Sobre — manual didatico do Vigia VPN Manager."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


SECTIONS: list[tuple[str, str]] = [
    (
        "O que faz",
        "Gerencia conexoes <b>WireGuard</b> com UI grafica. Lista perfis "
        "em <tt>/etc/wireguard/*.conf</tt>, conecta/desconecta com 1 clique "
        "e mostra status detalhado dos peers (handshake, dados transferidos, "
        "endpoints).\n\n"
        "Substitui o passo-a-passo manual:\n"
        "<tt>sudo cp meu.conf /etc/wireguard/</tt>\n"
        "<tt>sudo wg-quick up meu</tt>\n"
        "<tt>sudo wg show meu</tt>\n\n"
        "Cada operacao usa <b>1 dialog pkexec</b> — sem precisar abrir "
        "terminal."
    ),
    (
        "Como usar",
        "<b>1. Importar um perfil</b>:\n"
        "1. Aba <i>Perfis</i> → <i>Importar novo</i>\n"
        "2. Cole o conteudo do .conf (que voce recebeu do servidor VPN)\n"
        "3. Da um nome (sem .conf), ex: <tt>trabalho</tt>\n"
        "4. <i>Importar</i> — pede senha admin\n"
        "5. Arquivo vai pra <tt>/etc/wireguard/trabalho.conf</tt> com "
        "perms 0600 (so root)\n\n"
        "<b>2. Conectar</b>:\n"
        "1. Aba <i>Perfis</i>, clique <i>Carregar perfis</i> (pede senha 1x)\n"
        "2. Lista mostra os .conf disponiveis\n"
        "3. Clique <i>Conectar</i> no perfil desejado — pede senha\n"
        "4. Badge muda de 'off' (cinza) pra 'ON' (verde)\n\n"
        "<b>3. Ver status detalhado</b>:\n"
        "1. Aba <i>Status</i>\n"
        "2. Clique <i>Detalhes (admin)</i> para ver peers, handshake, "
        "bytes transferidos\n"
        "3. Expande cada interface para ver os peers conectados"
    ),
    (
        "Conceitos importantes",
        "<b>WireGuard</b> e' uma VPN moderna que prioriza simplicidade. "
        "Configuracao em arquivo de texto, criptografia state-of-the-art, "
        "kernel module nativo no Linux desde 5.6.\n\n"
        "<b>Arquivo .conf</b> contem:\n"
        "- <tt>[Interface]</tt>: sua chave privada + IP local + DNS\n"
        "- <tt>[Peer]</tt>: chave publica do servidor + endpoint + "
        "<tt>AllowedIPs</tt> (que rotas vao pelo tunel)\n\n"
        "<b>Permissoes</b>: <tt>/etc/wireguard/</tt> e' default mode 0700 "
        "(so root). Cada .conf 0600. Isso e' importante porque as chaves "
        "privadas estao la — se outros users lessem, podiam se passar por "
        "voce.\n\n"
        "<b>wg-quick</b> e' o helper que le o .conf e faz: criar a "
        "interface, configurar IP, adicionar rotas, configurar DNS. "
        "Versao manual seria <tt>ip link add</tt> + <tt>wg set</tt> + "
        "<tt>ip address add</tt> + <tt>ip route add</tt>."
    ),
    (
        "Limitacoes conhecidas",
        "- Apenas <b>WireGuard</b> nesta versao. OpenVPN vira em v0.2.\n"
        "- Status detalhado (handshake, transferred) requer <i>Modo admin</i> "
        "por refresh — <tt>wg show &lt;iface&gt;</tt> sem root mascara peers.\n"
        "- Sem editor visual do .conf — para editar, ainda precisa "
        "<tt>pkexec gnome-text-editor /etc/wireguard/&lt;nome&gt;.conf</tt>.\n"
        "- Sem auto-connect no boot. Para isso: "
        "<tt>sudo systemctl enable wg-quick@&lt;nome&gt;</tt>."
    ),
    (
        "Saiba mais",
        "- <tt>man wg</tt>, <tt>man wg-quick</tt>\n"
        "- Site oficial: https://www.wireguard.com\n"
        "- Gerador de chaves: <tt>wg genkey | tee privatekey | wg pubkey &gt; publickey</tt>\n"
        "- Quick reference: https://www.wireguard.com/quickstart/\n"
        "- VPNs WireGuard prontas (gratis ou pago): Mullvad, IVPN, ProtonVPN"
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
