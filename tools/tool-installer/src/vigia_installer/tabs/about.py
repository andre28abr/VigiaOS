"""Aba Sobre — manual didatico do Vigia Tool Installer."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


SECTIONS: list[tuple[str, str]] = [
    (
        "O que faz",
        "Mantém o <b>sistema</b> e os <b>programas instalados</b> em dia. "
        "Verifica se há atualizações e deixa você aplicar — pelo painel (um "
        "clique) ou copiando o comando pro terminal, do seu jeito."
    ),
    (
        "Como usar",
        "<b>Aba Atualizações</b>:\n"
        "1. Ao abrir, checa automaticamente se há atualizações\n"
        "2. <b>Atualizar agora</b> aplica tudo pelo painel "
        "(<tt>pkexec dnf upgrade</tt> — pede a senha de admin uma vez)\n"
        "3. Ou copie o comando e rode no <b>terminal</b>, se preferir\n"
        "4. O que será atualizado vem separado: <i>Sistema</i> (pacotes do "
        "Fedora) vs <i>Programas da suíte Vigia</i>"
    ),
    (
        "Conceitos importantes",
        "<b>Sem reboot</b>: o <tt>dnf</tt> aplica na hora. Atualizar <b>não "
        "liga serviço</b> nem muda configuração — é seguro.\n\n"
        "<b>Por que não tem mais catálogo?</b> A lista de ferramentas pra "
        "instalar saiu daqui — cada produto (Hub/Blue/Red) já mostra, com a "
        "<b>bolinha verde/vermelha</b>, se as dependências de cada módulo "
        "estão OK. Pra instalar o que falta, rode o instalador completo no "
        "terminal: <tt>./install/bootstrap.sh</tt>."
    ),
    (
        "Saiba mais",
        "- <tt>dnf check-update</tt> — ver o que tem atualização\n"
        "- <tt>sudo dnf upgrade</tt> — atualizar tudo pelo terminal\n"
        "- Instalador completo: <tt>install/bootstrap.sh</tt>\n"
        "- Fedora Workstation docs: https://docs.fedoraproject.org/en-US/workstation/"
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
