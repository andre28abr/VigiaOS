"""Aba Sobre — manual didatico do Vigia Privacy Controls."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


SECTIONS: list[tuple[str, str]] = [
    (
        "O que faz",
        "Centraliza <b>13 configurações de privacidade</b> do GNOME e do "
        "sistema num só painel. Cada switch muda o estado <b>real</b> do "
        "sistema imediatamente.\n\n"
        "Sem essa tool, você precisaria editar manualmente <tt>dconf</tt>, "
        "<tt>/etc/selinux/config</tt>, <tt>systemctl</tt> e <tt>firewall-cmd</tt> "
        "separadamente. Aqui, é um clique."
    ),
    (
        "Como usar",
        "<b>Modo leigo</b>: a maioria dos toggles é user-scope (sem senha). "
        "Ligue/desligue conforme preferência. Mudanças sincronizam com o "
        "GNOME Settings em tempo real.\n\n"
        "<b>Toggles que pedem senha</b> (admin via <tt>pkexec</tt>): "
        "firewall, servidor SSH e Tor. Você verá um dialog do polkit "
        "antes da mudança tomar efeito."
    ),
    (
        "Conceitos importantes",
        "<b>dconf</b> é o sistema de configuração do GNOME — equivalente "
        "ao registry do Windows mas mais simples. Cada toggle aqui mapeia "
        "para uma chave <tt>dconf</tt>.\n\n"
        "<b>User-scope vs system-scope</b>: user-scope altera só o seu "
        "perfil (no <tt>~/.config/dconf/user</tt>). System-scope altera "
        "serviços do sistema todo (precisa root).\n\n"
        "<b>Toggle indisponível</b>: aparece dimmed quando o backend não "
        "está presente (ex: bluetooth sem adaptador, firewall sem firewalld "
        "instalado)."
    ),
    (
        "Limitações conhecidas",
        "- Algumas mudanças (firewall, SSH) só persistem se você ligar "
        "<i>enable</i> também — esta tool faz <tt>--now</tt> (estado atual) "
        "mas não mexe em <i>enable/disable no boot</i>.\n"
        "- Bluetooth toggle requer <tt>bluetoothctl</tt> instalado.\n"
        "- Tor toggle só funciona se o pacote <tt>tor</tt> estiver "
        "instalado via Tool Installer."
    ),
    (
        "Saiba mais",
        "- <tt>man dconf</tt> — documentação do dconf\n"
        "- <tt>man systemctl</tt> — controle de serviços systemd\n"
        "- <tt>man firewall-cmd</tt> — controle do firewalld\n"
        "- Wiki Fedora: https://docs.fedoraproject.org/en-US/quick-docs/firewalld/"
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
