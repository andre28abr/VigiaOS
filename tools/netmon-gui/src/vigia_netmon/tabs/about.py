"""Aba Sobre — manual didatico do Vigia Network Monitor."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


SECTIONS: list[tuple[str, str]] = [
    (
        "O que faz",
        "Visualizador gráfico de <tt>ss -tunap</tt> com <b>auto-refresh</b>. "
        "Lista TODAS as conexões ativas (TCP + UDP, qualquer estado) com "
        "nome do processo e PID.\n\n"
        "Responde a perguntas como:\n"
        "- 'Que processo está conversando com esse IP estranho?'\n"
        "- 'Qual serviço está escutando na porta 5432?'\n"
        "- 'O que está exposto na rede agora?'"
    ),
    (
        "Como usar",
        "<b>Aba Conexões</b>:\n"
        "1. Lista atualiza automaticamente a cada 3 segundos\n"
        "2. Filtre por processo, IP ou porta na barra de busca\n"
        "3. Cores indicam o estado: <i>ESTAB</i> verde, <i>LISTEN</i> accent, "
        "<i>WAIT</i> âmbar\n\n"
        "<b>Aba Listening</b>: só servidores ativos no host. Crítico para "
        "saber <b>o que está exposto</b> — mesmo localhost pode ser "
        "tunelado, então tudo conta.\n\n"
        "<b>Modo admin (opt-in)</b>: liga o switch <i>Admin</i> no header. "
        "Revela nomes de processos do sistema (root) que normalmente "
        "aparecem como <i>(processo restrito)</i> — ex: <tt>NetworkManager</tt>, "
        "<tt>systemd-resolve</tt>, <tt>cupsd</tt>. Pede senha por refresh."
    ),
    (
        "Conceitos importantes",
        "<b>ss</b> (socket statistics) é o sucessor moderno do <tt>netstat</tt>. "
        "Roda diretamente sobre o netlink — muito mais rápido que parsear "
        "<tt>/proc/net/tcp</tt>.\n\n"
        "<b>Estados TCP comuns</b>:\n"
        "- <i>LISTEN</i>: servidor esperando conexões\n"
        "- <i>ESTAB</i>: conexão estabelecida e ativa\n"
        "- <i>TIME-WAIT</i>: conexão acabou de fechar (cleanup)\n"
        "- <i>CLOSE-WAIT</i>: peer fechou, mas você ainda não (anomalia "
        "se persistir)\n"
        "- <i>SYN-SENT</i>/<i>SYN-RECV</i>: handshake em andamento\n\n"
        "<b>UDP não tem estado</b> conexionalmente, mas <tt>ss</tt> mostra "
        "<i>UNCONN</i> para sockets bound não-conectados (servidores)."
    ),
    (
        "Limitações conhecidas",
        "- Auto-refresh roda <tt>ss</tt> sync — em máquinas com muitas "
        "conexões (>1000) pode ter latência perceptível\n"
        "- Sem DNS reverso ainda — IPs aparecem em forma numérica (v0.2)\n"
        "- Sem bandwidth por processo — para isso instale <tt>nethogs</tt> "
        "via Tool Installer (v0.2 integrará)"
    ),
    (
        "Saiba mais",
        "- <tt>man ss</tt> — flags e formatos\n"
        "- <tt>ss -tunap | grep ESTAB</tt> — equivalente CLI do filtro\n"
        "- <tt>lsof -i :PORTA</tt> — quem usa uma porta específica"
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
