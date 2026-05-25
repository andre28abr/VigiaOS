"""Aba Sobre — manual didatico do Vigia Firewall Manager."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


SECTIONS: list[tuple[str, str]] = [
    (
        "O que faz",
        "Wrapper grafico do <tt>firewall-cmd</tt> — substitui o "
        "<tt>firewall-config</tt> antigo. Pensado para o <b>dia-a-dia</b> "
        "de quem gerencia firewall do desktop:\n\n"
        "- Ligar/desligar o daemon firewalld\n"
        "- Mudar zona padrao\n"
        "- Adicionar/remover services (ssh, http, etc.) por zona\n"
        "- Adicionar/remover portas customizadas por zona\n\n"
        "Sem precisar lembrar dos comandos cheios de flags."
    ),
    (
        "Como usar",
        "<b>Cenario 1 — Verificar se o firewall esta ativo</b>:\n"
        "1. Aba <i>Status</i> mostra 'running' verde ou 'stopped' vermelho\n"
        "2. Botao <i>Start/Stop</i> permite alternar (precisa senha)\n\n"
        "<b>Cenario 2 — Liberar uma porta para um servico</b>:\n"
        "1. Aba <i>Zonas</i>, escolhe a zona (geralmente 'public' ou 'home')\n"
        "2. Em <i>Services</i>, clica '+' para adicionar (ex: ssh, http)\n"
        "3. Mudanca aplica imediatamente E persiste no boot "
        "(<tt>--permanent --reload</tt>)\n\n"
        "<b>Cenario 3 — Liberar porta customizada</b>:\n"
        "1. Aba <i>Zonas</i>, em <i>Portas</i> clica '+'\n"
        "2. Digite a porta (ex: 8080 ou range 8000-8010)\n"
        "3. Escolha protocolo TCP/UDP\n"
        "4. Confirma — pede senha"
    ),
    (
        "Conceitos importantes",
        "<b>firewalld</b> e' o gerenciador moderno de firewall do Fedora. "
        "Substitui o iptables direto com abstracoes de mais alto nivel.\n\n"
        "<b>Zonas</b> sao conjuntos de regras aplicadas conforme contexto "
        "da rede. Mais comuns:\n"
        "- <i>public</i>: estrito, default. Use em redes nao confiaveis\n"
        "- <i>home</i>: mais relaxado. Permite alguns services internos\n"
        "- <i>internal</i>: bem aberto. Use so em redes 100% confiaveis\n"
        "- <i>drop</i>: bloqueia tudo. Modo paranoia\n"
        "- <i>trusted</i>: SEM firewall na pratica (cuidado!)\n\n"
        "<b>Services pre-definidos</b>: o firewalld tem packs de regras "
        "para servicos conhecidos (ssh = porta 22 TCP, http = 80, etc.). "
        "Mais facil que decorar numeros de portas."
    ),
    (
        "Limitacoes conhecidas",
        "- Rich rules (rate-limit, log action, family=ipv6) ainda nao "
        "tem editor visual — use terminal (v0.2)\n"
        "- ICMP block, masquerade e port-forwarding ainda nao expostos\n"
        "- Mudancas sempre escrevem <tt>--permanent</tt> + reload. Nao ha "
        "opcao de 'so runtime'"
    ),
    (
        "Saiba mais",
        "- <tt>man firewall-cmd</tt> — referencia completa\n"
        "- <tt>firewall-cmd --get-services</tt> — lista services disponiveis\n"
        "- Fedora docs: https://docs.fedoraproject.org/en-US/quick-docs/firewalld/"
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
