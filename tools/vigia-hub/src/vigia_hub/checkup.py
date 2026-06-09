"""Painel "Tudo Certo?" — checkup de segurança do PC, embarcado no VigiaOS.

Agrega vigia_common.posture (atualizações, firewall, antivírus, privacidade)
num semáforo 🟢🟡🔴 com botão "Resolver" que leva pra ferramenta certa (via as
Gio actions show-tool / show-settings do app). Roda as checagens em thread.
"""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from vigia_common import posture

_STATUS_ICON = {
    posture.OK: "emblem-ok-symbolic",
    posture.WARN: "dialog-warning-symbolic",
    posture.BAD: "dialog-error-symbolic",
    posture.UNKNOWN: "dialog-question-symbolic",
}
_STATUS_CSS = {
    posture.OK: "success",
    posture.WARN: "warning",
    posture.BAD: "error",
    posture.UNKNOWN: "dim-label",
}
_OVERALL = {
    posture.OK: ("emblem-ok-symbolic", "Tudo certo!",
                 "Seu PC está com as proteções básicas em dia."),
    posture.WARN: ("dialog-warning-symbolic", "Alguns pontos de atenção",
                   "Nada grave, mas vale resolver os itens abaixo."),
    posture.BAD: ("dialog-error-symbolic", "Precisa de atenção",
                  "Há algo importante desligado — veja abaixo."),
    posture.UNKNOWN: ("dialog-question-symbolic", "Verificação incompleta",
                      "Algumas checagens não rodaram neste sistema."),
}
_CSS_CLASSES = ("success", "warning", "error", "dim-label", "accent")


class _Checkup:
    """Controller do painel (header + hero + lista de checagens)."""

    def __init__(self) -> None:
        # Hero (resumo geral)
        self._hero_icon = Gtk.Image.new_from_icon_name("emblem-synchronizing-symbolic")
        self._hero_icon.set_pixel_size(56)
        self._hero_icon.set_halign(Gtk.Align.CENTER)
        self._hero_title = Gtk.Label(label="Verificando…")
        self._hero_title.add_css_class("title-1")
        self._hero_desc = Gtk.Label(
            label="Checando atualizações, firewall, antivírus e privacidade.")
        self._hero_desc.add_css_class("dim-label")
        self._hero_desc.set_wrap(True)
        self._hero_desc.set_justify(Gtk.Justification.CENTER)

        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        hero.set_margin_top(28)
        hero.set_margin_bottom(20)
        hero.append(self._hero_icon)
        hero.append(self._hero_title)
        hero.append(self._hero_desc)

        # Lista de checagens
        self._group = Adw.PreferencesGroup()
        self._group.set_title("Verificações")
        self._rows: list[Gtk.Widget] = []

        page = Adw.PreferencesPage()
        page.add(self._group)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        body.append(hero)
        body.append(page)
        page.set_vexpand(True)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(body)

        # Header + botão "Verificar de novo"
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title="Tudo Certo?", subtitle=""))
        self._refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        self._refresh_btn.set_tooltip_text("Verificar de novo")
        self._refresh_btn.connect("clicked", lambda _b: self._run())
        header.pack_end(self._refresh_btn)

        self.toolbar = Adw.ToolbarView()
        self.toolbar.add_top_bar(header)
        self.toolbar.set_content(scrolled)

        self._running = False
        # Re-checa toda vez que a tela aparece (ex: voltou depois de atualizar a
        # base do antivírus) — não fica preso no resultado em cache.
        self.toolbar.connect("map", lambda *_a: self._run())

    # --------------------------------------------------------------
    def _run(self) -> None:
        if self._running:
            return
        self._running = True
        self._refresh_btn.set_sensitive(False)
        self._set_hero(posture.UNKNOWN, "Verificando…",
                       "Checando atualizações, firewall, antivírus e privacidade.")
        self._hero_icon.set_from_icon_name("emblem-synchronizing-symbolic")
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self) -> None:
        try:
            checks = posture.run_all()
        except Exception:  # pylint: disable=broad-except
            checks = []
        GLib.idle_add(self._render, checks)

    def _render(self, checks: list) -> bool:
        self._running = False
        self._refresh_btn.set_sensitive(True)

        overall = posture.overall_status(checks) if checks else posture.UNKNOWN
        icon, title, desc = _OVERALL[overall]
        self._hero_icon.set_from_icon_name(icon)
        self._set_hero(overall, title, desc)

        for r in self._rows:
            self._group.remove(r)
        self._rows = []

        for c in checks:
            row = Adw.ActionRow()
            row.set_title(c.label)
            row.set_subtitle(c.detail)
            row.set_subtitle_lines(0)
            dot = Gtk.Image.new_from_icon_name(
                _STATUS_ICON.get(c.status, "dialog-question-symbolic"))
            dot.add_css_class(_STATUS_CSS.get(c.status, "dim-label"))
            row.add_prefix(dot)
            if c.fix_tool and c.status != posture.OK:
                btn = Gtk.Button(label=c.fix_label or "Resolver")
                btn.set_valign(Gtk.Align.CENTER)
                btn.add_css_class("pill")
                btn.connect("clicked", self._on_fix, c.fix_tool)
                row.add_suffix(btn)
            self._group.add(row)
            self._rows.append(row)
        return False

    def _set_hero(self, status: str, title: str, desc: str) -> None:
        for cls in _CSS_CLASSES:
            self._hero_icon.remove_css_class(cls)
        self._hero_icon.add_css_class(_STATUS_CSS.get(status, "dim-label"))
        self._hero_title.set_label(title)
        self._hero_desc.set_label(desc)

    def _on_fix(self, _btn: Gtk.Button, fix_tool: str) -> None:
        app = Gio.Application.get_default()
        if app is None:
            return
        try:
            if fix_tool == "config":
                app.activate_action("show-settings", None)
            elif ":" in fix_tool:  # "toolid:aba" → abre a tool já na aba certa
                app.activate_action(
                    "show-tool-tab", GLib.Variant.new_string(fix_tool))
            elif fix_tool:
                app.activate_action(
                    "show-tool", GLib.Variant.new_string(fix_tool))
        except Exception:  # pylint: disable=broad-except
            pass


def build_content() -> Gtk.Widget:
    return _Checkup().toolbar
