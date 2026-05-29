"""Aba Sobre — manual didatico."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


SECTIONS: list[tuple[str, str]] = [
    (
        "O que faz",
        "Procura por <b>rootkits</b>, <b>backdoors</b> e <b>sinais de "
        "comprometimento</b> usando dois scanners clássicos:\n\n"
        "- <b>chkrootkit</b> — rápido (~30s), checks por binário\n"
        "- <b>Rootkit Hunter (rkhunter)</b> — completo (2-5min), 200+ checks\n\n"
        "Os dois são complementares. Rode periodicamente."
    ),
    (
        "Como usar",
        "1. Instale via Vigia Tool Installer (chkrootkit + rkhunter)\n"
        "2. Reinicie (rpm-ostree precisa)\n"
        "3. Abra a aba do scanner desejado\n"
        "4. Clique <i>Iniciar scan</i>, digite senha admin\n"
        "5. Output streama em tempo real (warnings amarelo, INFECTED vermelho)\n"
        "6. Resultado fica salvo no Histórico"
    ),
    (
        "Interpretando resultados",
        "<b>Limpo</b>: nenhum sinal. Sistema OK.\n\n"
        "<b>Warning</b>: possível falso positivo. Causas comuns:\n"
        "- Arquivos modificados após <tt>rpm-ostree upgrade</tt>\n"
        "- Modules proprietários (NVIDIA, VirtualBox)\n"
        "- Configs SSH OK no seu contexto\n\n"
        "<b>Infected</b>: alta probabilidade de comprometimento.\n"
        "1. Desconectar da rede\n"
        "2. Salvar o report\n"
        "3. Cruzar com Vigia File Integrity (AIDE)\n"
        "4. Considerar reinstalar"
    ),
    (
        "LGPD e privacidade",
        "100% offline. Reports JSON em "
        "<tt>~/.local/share/vigia-rootkit/scans/</tt> com mode 0600."
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
