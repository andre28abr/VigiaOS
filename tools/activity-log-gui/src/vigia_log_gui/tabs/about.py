"""Aba Sobre — manual didatico do Vigia Activity Log."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


SECTIONS: list[tuple[str, str]] = [
    (
        "O que faz",
        "Frontend GTK4 do <tt>vigia-log</tt> (parser Rust). Consolida tres "
        "fontes de log do sistema numa <b>unica linha do tempo human-readable</b>:\n\n"
        "- <tt>/var/log/audit/audit.log</tt> — kernel/SELinux events\n"
        "- <tt>systemd journal</tt> — services\n"
        "- <tt>/var/log/fail2ban.log</tt> — banimentos automaticos\n\n"
        "Traduz formato cru para frases em portugues como <i>'fail2ban "
        "baniu 192.0.2.42 apos 3 tentativas SSH em 10s'</i>."
    ),
    (
        "Como usar",
        "<b>1. Atualizar</b>: clique no botao refresh no header. Polkit "
        "pede senha 1x se <i>Modo admin</i> estiver ligado.\n\n"
        "<b>2. Status</b>: visao geral de KPIs (total de eventos, suspicious "
        "vs interesting vs routine) e quais fontes foram coletadas.\n\n"
        "<b>3. Timeline</b>: lista cronologica completa. Filtros:\n"
        "- Severidade (Suspicious / Interesting+ / Todas)\n"
        "- Fonte (audit / journal / fail2ban)\n"
        "- Busca por texto livre na narrativa\n"
        "- Click no evento expande mostrando o payload JSON cru\n\n"
        "<b>4. Correlations</b>: padroes cross-source detectados (ex: "
        "<tt>fail2ban_burst</tt>, <tt>oom_kill</tt>, <tt>selinux_burst</tt>)."
    ),
    (
        "Conceitos importantes",
        "<b>Severity classifier</b>: cada evento e' classificado em "
        "<i>routine</i>, <i>interesting</i> ou <i>suspicious</i>. Reduz ruido "
        "em ate 98% num audit.log tipico — voce so olha o que importa.\n\n"
        "<b>Correlations cross-source</b>: padroes que so fazem sentido "
        "vendo eventos de FONTES DIFERENTES juntos. Ex: 3 falhas SSH no "
        "audit + 1 ban no fail2ban = correlation <tt>fail2ban_burst</tt> com "
        "narrativa sintetizada.\n\n"
        "<b>Modo admin</b> via <tt>pkexec</tt>: necessario para ler audit.log "
        "(restrito a root) e journal do sistema. UM dialog cobre todas as "
        "fontes."
    ),
    (
        "Limitacoes conhecidas",
        "- Sem live tail (auto-refresh) — clique manual no botao Atualizar\n"
        "- Limite default de 500 eventos POR fonte. Use CLI "
        "<tt>vigia-log --limit 5000</tt> para mais\n"
        "- Filtro temporal (last hour, etc.) so via CLI por enquanto"
    ),
    (
        "Saiba mais",
        "- <tt>vigia-log --help</tt> — CLI do engine Rust\n"
        "- <tt>vigia-log --output json-bundle</tt> — formato consumido por "
        "esta GUI (util para scripts)\n"
        "- <tt>man journalctl</tt>, <tt>man ausearch</tt> — fontes upstream\n"
        "- Codigo: <tt>tools/activity-log/</tt> (Rust), "
        "<tt>tools/activity-log-gui/</tt> (Python)"
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
