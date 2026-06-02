"""GUI do Vigia Playbooks — abas Playbooks / Histórico / Sobre.

Exporta `build_content() -> Gtk.Widget`, embarcado pelo shell via `Module.impl`.
Cada playbook é um cartão expansível com checklist clicável; ao registrar, salva
um atendimento datado (trilha 0600). GTK só é importado aqui.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from . import backend  # noqa: E402

_SEVERITY = {
    "info": ("Info", "dialog-information-symbolic", "accent"),
    "baixo": ("Baixo", "dialog-information-symbolic", "accent"),
    "suspeito": ("Suspeito", "dialog-warning-symbolic", "warning"),
    "alto": ("Alto", "dialog-error-symbolic", "error"),
    "critico": ("Crítico", "dialog-error-symbolic", "error"),
}


def _sev(sev: str) -> tuple[str, str, str]:
    return _SEVERITY.get((sev or "").lower(),
                         ("—", "dialog-information-symbolic", "accent"))


def build_content() -> Gtk.Widget:
    stack = Adw.ViewStack()
    stack.add_titled_with_icon(_PlaybooksView(), "pb", "Playbooks",
                               "emblem-documents-symbolic")
    stack.add_titled_with_icon(_HistoryView(), "hist", "Histórico",
                               "document-open-recent-symbolic")
    stack.add_titled_with_icon(_build_about(), "sobre", "Sobre",
                               "help-about-symbolic")
    switcher = Adw.ViewSwitcher()
    switcher.set_stack(stack)
    switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
    header = Adw.HeaderBar()
    header.set_title_widget(switcher)
    tv = Adw.ToolbarView()
    tv.add_top_bar(header)
    tv.set_content(stack)
    return tv


# ============================================================
# Cartão de um playbook (ExpanderRow com checklist + notas + registrar)
# ============================================================


class _PlaybookExpander(Adw.ExpanderRow):
    def __init__(self, pb: backend.Playbook, on_saved) -> None:
        super().__init__()
        self._pb = pb
        self._on_saved = on_saved
        self._checks: dict[str, Gtk.CheckButton] = {}

        label, icon, css = _sev(pb.severity)
        self.set_title(pb.title)
        self.set_subtitle(pb.when)
        self.set_subtitle_lines(0)
        img = Gtk.Image.new_from_icon_name(icon)
        if css in ("warning", "error"):
            img.add_css_class(css)
        self.add_prefix(img)
        pill = Gtk.Label(label=label)
        pill.add_css_class("caption")
        if css in ("warning", "error"):
            pill.add_css_class(css)
        self.add_suffix(pill)

        # passos por fase
        for pi, phase in enumerate(pb.phases):
            head = Adw.ActionRow()
            head.set_title(phase.name)
            head.add_css_class("heading")
            head.set_activatable(False)
            self.add_row(head)
            for si, step in enumerate(phase.steps):
                key = backend.step_key(pi, si)
                row = Adw.ActionRow()
                row.set_title(step.text)
                if step.detail:
                    row.set_subtitle(step.detail)
                    row.set_subtitle_lines(0)
                chk = Gtk.CheckButton()
                chk.set_valign(Gtk.Align.CENTER)
                row.add_prefix(chk)
                row.set_activatable_widget(chk)
                self._checks[key] = chk
                self.add_row(row)

        # notas
        self._notes = Adw.EntryRow()
        self._notes.set_title("Notas do atendimento")
        self.add_row(self._notes)

        # registrar
        save_row = Adw.ActionRow()
        save_row.set_title("Registrar atendimento")
        save_row.set_subtitle("Salva os passos marcados + notas (trilha 0600)")
        save_row.set_subtitle_lines(0)
        btn = Gtk.Button(label="Registrar")
        btn.add_css_class("suggested-action")
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked", self._on_save)
        save_row.add_suffix(btn)
        save_row.set_activatable_widget(btn)
        self.add_row(save_row)

    def _on_save(self, _btn: Gtk.Button) -> None:
        inc = backend.start_incident(self._pb)
        inc.done_steps = [k for k, c in self._checks.items() if c.get_active()]
        inc.notes = self._notes.get_text()
        done, total = backend.progress(inc, self._pb)
        inc.closed = done == total and total > 0
        path = backend.save_incident(inc)
        if path:
            self.set_subtitle(
                f"✓ Registrado: {done}/{total} passos · {inc.started_at}"
            )
            if self._on_saved:
                self._on_saved()


class _PlaybooksView(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        page = Adw.PreferencesPage()
        page.set_vexpand(True)
        self.append(page)
        g = Adw.PreferencesGroup()
        g.set_title("Roteiros de resposta a incidentes")
        g.set_description(
            "Escolha o roteiro conforme o tipo de incidente, siga os passos "
            "marcando o que foi feito, anote e clique em Registrar. Cada "
            "atendimento vira uma trilha datada (aparece no Histórico)."
        )
        for pb in backend.playbooks():
            g.add(_PlaybookExpander(pb, on_saved=None))
        page.add(g)


# ============================================================
# Aba Histórico
# ============================================================


class _HistoryView(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._page = Adw.PreferencesPage()
        self._page.set_vexpand(True)
        self.append(self._page)
        self._group = Adw.PreferencesGroup()
        self._group.set_title("Atendimentos registrados")
        refresh = Gtk.Button(label="Atualizar")
        refresh.add_css_class("flat")
        refresh.connect("clicked", lambda _b: self._reload())
        self._group.set_header_suffix(refresh)
        self._page.add(self._group)
        self._rows: list[Gtk.Widget] = []
        self._reload()

    def _reload(self) -> None:
        for r in self._rows:
            self._group.remove(r)
        self._rows = []
        incidents = backend.list_incidents()
        if not incidents:
            row = Adw.ActionRow()
            row.set_title("Nenhum atendimento registrado ainda.")
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
            self._group.add(row)
            self._rows.append(row)
            return
        for inc in incidents:
            n = len(inc.get("done_steps", []))
            row = Adw.ActionRow()
            row.set_title(inc.get("playbook_title", "?"))
            row.set_subtitle(
                f"{inc.get('started_at', '?')} · {n} passo(s) marcados"
                + ("  ·  encerrado" if inc.get("closed") else "")
            )
            row.set_subtitle_lines(0)
            icon = "emblem-ok-symbolic" if inc.get("closed") else "emblem-documents-symbolic"
            row.add_prefix(Gtk.Image.new_from_icon_name(icon))
            self._group.add(row)
            self._rows.append(row)


# ============================================================
# Aba Sobre
# ============================================================


def _build_about() -> Gtk.Widget:
    page = Adw.PreferencesPage()
    g = Adw.PreferencesGroup()
    g.set_title("Vigia Playbooks")
    g.set_description(
        "Roteiros guiados de resposta a incidentes (contenção → erradicação → "
        "recuperação → notificação) com trilha de auditoria. Módulo de Resposta "
        "a Incidentes do VigiaBlue. Não depende de ferramenta externa. Cada "
        "atendimento é salvo localmente com permissão 0600."
    )
    row = Adw.ActionRow()
    row.set_title("Por que registrar")
    row.set_subtitle(
        "A LGPD (art. 48) exige comunicar incidentes com dados pessoais à ANPD "
        "e aos titulares. A trilha datada é a prova de diligência."
    )
    row.set_subtitle_lines(0)
    row.add_prefix(Gtk.Image.new_from_icon_name("security-high-symbolic"))
    g.add(row)
    page.add(g)
    return page
