"""Aba Sobre — manual didatico do Vigia Tool Installer."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


SECTIONS: list[tuple[str, str]] = [
    (
        "O que faz",
        "Catálogo de <b>16 ferramentas de segurança</b> curadas para "
        "Fedora Silverblue. Cada item tem descrição em pt-BR e um <i>por "
        "que você quer isso</i> que dá contexto prático.\n\n"
        "Instala via <tt>rpm-ostree install</tt> com UM clique. Sem precisar "
        "abrir terminal ou lembrar nomes de pacote."
    ),
    (
        "Como usar",
        "<b>Aba Catálogo</b>:\n"
        "1. Tools agrupadas por categoria (Auditoria, Rede, Monitoramento, "
        "Privacidade, Forense)\n"
        "2. Cada row tem badge de status (<i>Disponível</i>, <i>Instalado</i>, "
        "<i>Pendente</i>)\n"
        "3. Expande a row clicando na seta — vê o <i>por que você quer "
        "isso</i> + nome do pacote\n"
        "4. <i>Instalar</i> dispara <tt>pkexec rpm-ostree install &lt;pkg&gt;</tt>\n\n"
        "<b>Aba Pendentes</b>:\n"
        "- Lista pacotes staged que serão aplicados no próximo boot\n"
        "- Botão <i>Reiniciar agora</i> aplica imediatamente\n\n"
        "<b>Dica</b>: instale várias tools em sequência, depois reinicie "
        "uma vez. Cada install demora 1-3 min."
    ),
    (
        "Conceitos importantes",
        "<b>Silverblue é atômico</b>: <tt>dnf install</tt> NÃO funciona. "
        "Pacotes são aplicados como camadas via <tt>rpm-ostree</tt> e só "
        "tomam efeito após reboot. Esta tool é específica pra esse "
        "modelo.\n\n"
        "<b>Layered packages</b> vs <b>image rebase</b>:\n"
        "- <i>Layer</i>: <tt>rpm-ostree install</tt> adiciona um pacote por "
        "cima. Pode acumular vários.\n"
        "- <i>Rebase</i>: <tt>rpm-ostree rebase</tt> troca a imagem base "
        "inteira. Esta tool não mexe nisso.\n\n"
        "<b>Catálogo curado</b>: não é uma lista exaustiva. São ferramentas "
        "que o Vigia considera <i>úteis para o contexto de segurança</i>. "
        "Para instalar outros pacotes, use <tt>rpm-ostree install</tt> "
        "direto."
    ),
    (
        "Limitações conhecidas",
        "- Sem multi-select ainda (v0.2 vai permitir checkboxes + 1 transação)\n"
        "- Sem busca em repos externos — só o catálogo curado\n"
        "- Algumas instalações podem demorar muito (5-10 min) se houver "
        "muitas dependências"
    ),
    (
        "Saiba mais",
        "- <tt>rpm-ostree status</tt> — ver pacotes layered atuais\n"
        "- <tt>rpm-ostree reset</tt> — remover TODAS as camadas "
        "(volta pra imagem base)\n"
        "- Catálogo: <tt>tools/tool-installer/src/vigia_installer/catalog.py</tt>\n"
        "- Fedora Silverblue docs: https://docs.fedoraproject.org/en-US/fedora-silverblue/"
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
