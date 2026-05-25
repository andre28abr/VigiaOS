"""Aba Sobre — manual didatico do Vigia Network Monitor."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


SECTIONS: list[tuple[str, str]] = [
    (
        "O que faz",
        "Visualizador grafico de <tt>ss -tunap</tt> com <b>auto-refresh</b>. "
        "Lista TODAS as conexoes ativas (TCP + UDP, qualquer estado) com "
        "nome do processo e PID.\n\n"
        "Responde a perguntas como:\n"
        "- 'Que processo esta conversando com esse IP estranho?'\n"
        "- 'Qual servico esta escutando na porta 5432?'\n"
        "- 'O que esta exposto na rede agora?'"
    ),
    (
        "Como usar",
        "<b>Aba Conexoes</b>:\n"
        "1. Lista atualiza automaticamente a cada 3 segundos\n"
        "2. Filtre por processo, IP ou porta na barra de busca\n"
        "3. Cores indicam o estado: <i>ESTAB</i> verde, <i>LISTEN</i> accent, "
        "<i>WAIT</i> ambar\n\n"
        "<b>Aba Listening</b>: so servidores ativos no host. Critico para "
        "saber <b>o que esta exposto</b> — mesmo localhost pode ser "
        "tunelado, ent ao tudo conta.\n\n"
        "<b>Modo admin (opt-in)</b>: liga o switch <i>Admin</i> no header. "
        "Revela nomes de processos do sistema (root) que normalmente "
        "aparecem como <i>(processo restrito)</i> — ex: <tt>NetworkManager</tt>, "
        "<tt>systemd-resolve</tt>, <tt>cupsd</tt>. Pede senha por refresh."
    ),
    (
        "Conceitos importantes",
        "<b>ss</b> (socket statistics) e' o sucessor moderno do <tt>netstat</tt>. "
        "Roda diretamente sobre o netlink — muito mais rapido que parsear "
        "<tt>/proc/net/tcp</tt>.\n\n"
        "<b>Estados TCP comuns</b>:\n"
        "- <i>LISTEN</i>: servidor esperando conexoes\n"
        "- <i>ESTAB</i>: conexao estabelecida e ativa\n"
        "- <i>TIME-WAIT</i>: conexao acabou de fechar (cleanup)\n"
        "- <i>CLOSE-WAIT</i>: peer fechou, mas voce ainda nao (anomalia "
        "se persistir)\n"
        "- <i>SYN-SENT</i>/<i>SYN-RECV</i>: handshake em andamento\n\n"
        "<b>UDP nao tem estado</b> conexionalmente, mas <tt>ss</tt> mostra "
        "<i>UNCONN</i> para sockets bound nao-conectados (servidores)."
    ),
    (
        "Limitacoes conhecidas",
        "- Auto-refresh roda <tt>ss</tt> sync — em maquinas com muitas "
        "conexoes (>1000) pode ter latencia perceptivel\n"
        "- Sem DNS reverso ainda — IPs aparecem em forma numerica (v0.2)\n"
        "- Sem bandwidth por processo — para isso instale <tt>nethogs</tt> "
        "via Tool Installer (v0.2 integrara)"
    ),
    (
        "Saiba mais",
        "- <tt>man ss</tt> — flags e formatos\n"
        "- <tt>ss -tunap | grep ESTAB</tt> — equivalente CLI do filtro\n"
        "- <tt>lsof -i :PORTA</tt> — quem usa uma porta especifica"
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
