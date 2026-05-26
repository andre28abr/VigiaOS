"""Aba Sobre — manual didatico do Vigia Reports."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


SECTIONS: list[tuple[str, str]] = [
    (
        "O que faz",
        "Gera relatorios <b>HTML</b> a partir de logs do sistema "
        "(<tt>journalctl</tt>, <tt>last</tt>, <tt>lastb</tt>). HTMLs sao "
        "prontos para impressao em PDF via Firefox/Chromium (Ctrl+P).\n\n"
        "Templates com KPIs no topo + tabelas detalhadas + estilo "
        "profissional (paleta zinc + emerald). Pensado para:\n"
        "- Revisao mensal de atividade\n"
        "- Compliance LGPD\n"
        "- Resposta a incidente\n"
        "- Auditoria por terceiros"
    ),
    (
        "Como usar",
        "<b>Aba Gerar</b>:\n"
        "1. Escolha o modelo (combo): 'Atividade geral' ou 'Eventos de "
        "autenticacao'\n"
        "2. Escolha o periodo (24h, 7 dias, 30 dias, 90 dias)\n"
        "3. Liga <i>Modo admin</i> se quiser dados completos (audit, "
        "journal do sistema, lastb). Pede senha 1x.\n"
        "4. <i>Gerar</i> — progress pulsante por alguns segundos\n"
        "5. HTML abre automaticamente no Firefox\n\n"
        "<b>Para gerar PDF</b>: no Firefox, <tt>Ctrl+P</tt> → Destino "
        "<i>Salvar como PDF</i>. CSS ja tem <tt>@media print</tt> — fica "
        "limpo.\n\n"
        "<b>Aba Biblioteca</b>: lista HTMLs salvos em "
        "<tt>~/.local/share/vigia-reports/</tt>. Botoes Abrir e Excluir."
    ),
    (
        "Conceitos importantes",
        "<b>Por que HTML e nao PDF direto?</b> Gerar PDF via Python "
        "(WeasyPrint, ReportLab) requer libcairo+pango+gdk-pixbuf que sao "
        "chatos em Silverblue. Firefox/Chromium ja imprimem com fidelidade "
        "visual identica via Ctrl+P. Stack leve, output igual.\n\n"
        "<b>Modo admin</b>: sem ele, <tt>journalctl --system</tt> nao "
        "retorna dados (restrito) e <tt>lastb</tt> precisa root. Com ele, "
        "<tt>pkexec</tt> faz UMA chamada combinada com todos os comandos.\n\n"
        "<b>LGPD</b>: os HTMLs sao salvos com perms <tt>0600</tt> e diretorio "
        "<tt>0700</tt> (so seu user le). Conteudo inclui IPs, comandos sudo, "
        "logins falhados — sensivel."
    ),
    (
        "Limitacoes conhecidas",
        "- Apenas 2 templates v0.1. v0.2 trara <i>compliance LGPD</i> e "
        "<i>incident response</i> dedicados\n"
        "- Sem agendamento automatico — v0.2 trara systemd timer opt-in\n"
        "- Templates fixos — personalizacao requer editar "
        "<tt>vigia_reports/templates/*.html</tt>"
    ),
    (
        "Saiba mais",
        "- Templates HTML: <tt>tools/reports/src/vigia_reports/templates/</tt>\n"
        "- <tt>man journalctl</tt> — coletor principal\n"
        "- Pasta dos relatorios: <tt>~/.local/share/vigia-reports/</tt>"
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
