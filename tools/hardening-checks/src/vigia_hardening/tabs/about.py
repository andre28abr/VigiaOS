"""Aba Sobre — manual didatico do Vigia Hardening Checks."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


SECTIONS: list[tuple[str, str]] = [
    (
        "O que faz",
        "Roda o <b>Lynis</b> (~250 controles de segurança) e mostra o "
        "resultado numa interface escaneável, em vez do wall-of-text do "
        "terminal. A métrica principal é o <b>Hardening Index</b> (0–100) "
        "— quanto maior, melhor a postura geral do sistema.\n\n"
        "Útil para <b>demonstrar postura LGPD</b> num escritório de "
        "advocacia ou outro contexto regulado."
    ),
    (
        "Como usar",
        "<b>Primeira vez</b>:\n"
        "1. Aba <i>Resumo</i>, clique 'Executar' (suggested-action azul)\n"
        "2. Polkit pede senha 1x — Lynis precisa root para varios checks\n"
        "3. Progress bar pulsante por 2-5 minutos\n"
        "4. Resultado aparece: Hardening Index + warnings + suggestions\n\n"
        "<b>Periodicamente</b>:\n"
        "- Aba <i>Warnings</i>: trate primeiro (criticidades imediatas)\n"
        "- Aba <i>Suggestions</i>: melhorias incrementais\n"
        "- Aba <i>Categorias</i>: visão agregada por área (AUTH, BOOT, "
        "KRNL, MACF, etc.)\n\n"
        "Cada finding tem um <tt>test-id</tt> (ex: <tt>KRNL-5820</tt>). "
        "Google esse ID para ver a remediation oficial do Lynis."
    ),
    (
        "Conceitos importantes",
        "<b>Hardening Index</b> é calculado pelo Lynis baseado no ratio "
        "de testes passed / total. Escala:\n"
        "- 85-100: Excelente\n"
        "- 75-84: Bom\n"
        "- 60-74: Razoável\n"
        "- 40-59: Insuficiente\n"
        "- 0-39: Crítico\n\n"
        "<b>Warnings vs Suggestions</b>:\n"
        "- <i>Warning</i> (críticas): problemas que merecem atenção "
        "imediata (ex: senha de root não configurada)\n"
        "- <i>Suggestion</i> (melhorias): hardening incremental "
        "(ex: configurar mínimo password age)\n\n"
        "<b>Tests skipped</b>: o Lynis pula testes que não se aplicam à sua "
        "máquina (ex: checagem de um serviço que você não tem instalado). "
        "Um número moderado de testes pulados é normal, não é bug."
    ),
    (
        "Limitações conhecidas",
        "- Audit do Lynis é read-only — NÃO corrige nada, só reporta\n"
        "- Algumas suggestions podem não se aplicar ao seu caso, mas o Lynis "
        "ainda lista (ex: 'instalar antivirus' quando o ClamAV já existe)\n"
        "- Sem comparação temporal (run1 vs run2) — v0.2 vai trazer"
    ),
    (
        "Saiba mais",
        "- <tt>man lynis</tt> — opcoes da CLI\n"
        "- <tt>sudo lynis show test KRNL-5820</tt> — detalhes de um test "
        "especifico\n"
        "- Site oficial: https://cisofy.com/lynis/\n"
        "- Report bruto: <tt>/var/log/lynis-report.dat</tt> "
        "(formato chave=valor)"
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
