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
        "Fedora Workstation. Cada item tem descrição em pt-BR e um <i>por "
        "que você quer isso</i> que dá contexto prático.\n\n"
        "Instala via <tt>dnf</tt> com UM clique. Sem precisar abrir terminal "
        "ou lembrar nomes de pacote."
    ),
    (
        "Como usar",
        "<b>Aba Catálogo</b>:\n"
        "1. Tools agrupadas por categoria (Auditoria, Rede, Monitoramento, "
        "Privacidade, Forense)\n"
        "2. Cada row tem badge de status (<i>Disponível</i> / <i>Instalado</i>)\n"
        "3. Expande a row clicando na seta — vê o <i>por que você quer "
        "isso</i> + nome do pacote\n"
        "4. <i>Instalar</i> dispara <tt>pkexec dnf install -y &lt;pkg&gt;</tt> "
        "— aplica na hora, sem reboot\n\n"
        "<b>Aba Atualizações</b>:\n"
        "- Checa atualizações do sistema (<tt>dnf check-update</tt>) ao abrir\n"
        "- Atualiza pelo painel (<i>Atualizar agora</i>) ou copia o comando "
        "pro terminal\n"
        "- Separa o que é do sistema do que é da suíte Vigia"
    ),
    (
        "Conceitos importantes",
        "<b>Instalação via dnf</b>: cada <i>Instalar</i> roda "
        "<tt>pkexec dnf install -y &lt;pkg&gt;</tt> — pede a senha de admin "
        "UMA vez (polkit) e aplica imediatamente, sem reiniciar.\n\n"
        "<b>Catálogo curado</b>: não é uma lista exaustiva. São ferramentas "
        "que o Vigia considera <i>úteis para o contexto de segurança</i>. "
        "Para instalar outros pacotes, use <tt>sudo dnf install</tt> direto.\n\n"
        "<b>Sem serviço ligado</b>: instalar uma ferramenta NÃO liga nenhum "
        "serviço — você ativa o que quiser na ferramenta correspondente "
        "(minimum surface area / LGPD)."
    ),
    (
        "Limitações conhecidas",
        "- Sem multi-select ainda (instalação é uma de cada vez)\n"
        "- Sem busca em repos externos — só o catálogo curado\n"
        "- Algumas instalações podem demorar (dependências grandes)"
    ),
    (
        "Saiba mais",
        "- <tt>dnf list --installed</tt> — ver o que está instalado\n"
        "- <tt>sudo dnf remove &lt;pkg&gt;</tt> — remover um pacote\n"
        "- Catálogo: <tt>tools/tool-installer/src/vigia_installer/catalog.py</tt>\n"
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
