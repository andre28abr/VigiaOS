"""Aba Sobre — manual didatico."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


SECTIONS: list[tuple[str, str]] = [
    (
        "O que faz",
        "Audita Linux <b>capabilities</b> no sistema. Mostra TODOS os "
        "binarios que tem capabilities setadas via <tt>setcap</tt>, com "
        "classificacao de risco (ALTO / MEDIO / BAIXO).\n\n"
        "Util pra responder perguntas como:\n"
        "- Que binarios podem manipular rede sem ser root?\n"
        "- Algum binario inesperado tem <tt>cap_sys_admin</tt>?\n"
        "- Apos um upgrade do sistema, mudou alguma capability?\n\n"
        "Ferramenta read-only nesta v0.1: <b>nao modifica</b> capabilities "
        "(seria via <tt>setcap</tt>). Modificacao chega na v0.2."
    ),
    (
        "Como usar",
        "<b>1. Fazer scan</b>:\n"
        "- Aba <i>Visao Geral</i>\n"
        "- <i>Escanear</i> (recomendado) — pede senha 1x, faz scan completo\n"
        "- <i>Quick scan</i> — sem pkexec, so paths user-readable\n\n"
        "<b>2. Investigar</b>:\n"
        "- Hero card mostra binarios encontrados + numero de caps de risco ALTO\n"
        "- KPIs detalhados na PreferencesGroup\n"
        "- Aba <i>Binarios</i> lista cada um — expandivel pra ver TODAS as caps\n"
        "- Search filtra por path ou nome de capability\n"
        "- Dropdown filtra por classe de risco\n\n"
        "<b>3. Aprender</b>:\n"
        "- Aba <i>Capabilities</i> tem o catalogo das ~40 caps do Linux\n"
        "- Cada uma com descricao pt-BR e classe de risco\n"
        "- Search e filtros pra encontrar uma especifica"
    ),
    (
        "Conceitos importantes",
        "<b>Linux capabilities</b> substituem o tradicional 'tudo ou nada' "
        "do root. Em vez de um binario precisar ser SUID root (rodando com "
        "TODOS os poderes), recebe apenas as caps que realmente precisa.\n\n"
        "<b>Exemplo classico</b>: <tt>/usr/bin/ping</tt>. Para mandar ICMP "
        "echo precisa de raw socket. Antes era SUID root (perigoso — bug no "
        "ping = compromisso root). Hoje so tem <tt>cap_net_raw=ep</tt> — "
        "muito menos superficie de ataque.\n\n"
        "<b>Sintaxe getcap</b>: <tt>cap_name+flags</tt>. Flags comuns:\n"
        "- <tt>e</tt> = effective (cap usada no ato)\n"
        "- <tt>i</tt> = inheritable (passada para filhos)\n"
        "- <tt>p</tt> = permitted (capacidade que pode usar via prctl)\n"
        "Tipicamente voce ve <tt>=ep</tt> em binarios — habilitada por padrao.\n\n"
        "<b>Sinais de alerta</b>:\n"
        "- Binario em <tt>/tmp</tt>, <tt>/home</tt> com QUALQUER cap = suspeito\n"
        "- <tt>cap_sys_admin</tt>, <tt>cap_setuid</tt>, <tt>cap_dac_override</tt> "
        "em binarios que voce nao conhece = INVESTIGUE\n"
        "- Apos comprometimento, atacante pode usar <tt>setcap</tt> em um shell "
        "(<tt>/usr/local/bin/bash</tt>) pra ter shell privilegiado persistente"
    ),
    (
        "Limitacoes conhecidas",
        "- Read-only nesta v0.1 — nao adiciona/remove capabilities via "
        "<tt>setcap</tt>. Para isso, use o terminal por agora.\n"
        "- Scan completo (com pkexec) leva 5-30 segundos dependendo do "
        "sistema. Quick scan e' instantaneo mas perde paths em /root, /var.\n"
        "- Nao inspeciona <b>thread capabilities</b> (caps dinamicas em "
        "runtime via prctl). So caps de arquivo (filesystem caps).\n"
        "- Catalogo de risco e' opiniao informada — algumas caps consideradas "
        "MEDIO podem ser ALTO num threat model especifico."
    ),
    (
        "Saiba mais",
        "- <tt>man capabilities(7)</tt> — referencia oficial\n"
        "- <tt>man getcap</tt>, <tt>man setcap</tt>\n"
        "- <tt>getcap -r /usr 2>/dev/null</tt> — comando equivalente ao "
        "Quick scan\n"
        "- <tt>sudo getcap -r / 2>/dev/null</tt> — equivalente ao scan completo\n"
        "- Linux kernel docs: https://www.kernel.org/doc/html/latest/security/credentials.html\n"
        "- GTFOBins lista binarios SUID/cap exploitable: https://gtfobins.github.io/"
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
