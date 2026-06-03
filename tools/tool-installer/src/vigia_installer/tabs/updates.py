"""Tab Atualizacoes: checa e aplica updates do sistema (dnf).

Substitui a antiga aba 'Pendentes'. Reune tudo sobre manter o sistema em dia:

- **Checagem automatica** ao abrir (notificacao "ali", no proprio painel): roda
  `dnf check-update` (read-only, sem root).
- **Dois caminhos pra atualizar** (o usuario escolhe):
  - *Pelo painel*: botao "Atualizar agora" → `pkexec dnf upgrade -y`.
  - *Pelo terminal*: comando copiavel pra rodar no terminal do sistema.
- **Lista de pacotes** com atualizacao, separada por origem (sistema vs suite).
"""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from ..catalog import find_by_package
from ._helpers import make_clamp, show_error
from vigia_common.helpers import copy_to_clipboard


class UpdatesTab(Adw.Bin):
    """Checa/aplica atualizacoes do sistema (dnf upgrade)."""

    def __init__(self) -> None:
        super().__init__()
        self._working = False
        self._dyn_rows: list[Gtk.Widget] = []

        # ---- Hero (resultado da checagem) ----
        self._hero = Gtk.Label(label="Verificando atualizações…")
        self._hero.add_css_class("title-1")
        self._hero.set_halign(Gtk.Align.CENTER)
        self._hero.set_margin_top(32)

        self._hero_sub = Gtk.Label(label="")
        self._hero_sub.add_css_class("title-4")
        self._hero_sub.add_css_class("dim-label")
        self._hero_sub.set_halign(Gtk.Align.CENTER)
        self._hero_sub.set_wrap(True)
        self._hero_sub.set_justify(Gtk.Justification.CENTER)
        self._hero_sub.set_max_width_chars(52)
        self._hero_sub.set_margin_bottom(20)

        # ---- Acoes (painel) ----
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        action_box.set_halign(Gtk.Align.CENTER)
        action_box.set_margin_bottom(20)

        self._update_btn = Gtk.Button(label="Atualizar agora")
        self._update_btn.add_css_class("suggested-action")
        self._update_btn.set_sensitive(False)
        self._update_btn.connect("clicked", self._on_update_now)
        action_box.append(self._update_btn)

        self._check_btn = Gtk.Button(label="Buscar atualizações")
        self._check_btn.connect("clicked", lambda _b: self.recheck())
        action_box.append(self._check_btn)

        # ---- Atualizar pelo terminal (comando copiavel) ----
        self._term_group = Adw.PreferencesGroup()
        self._term_group.set_title("Atualizar pelo terminal")
        self._term_group.set_description(
            "Prefere fazer no terminal do sistema? Copie o comando abaixo e "
            "rode (usa o dnf)."
        )
        cmd_row = Adw.ActionRow()
        cmd_row.set_title("Comando")
        cmd_lbl = Gtk.Label(label=backend.update_command_display())
        cmd_lbl.add_css_class("monospace")
        cmd_lbl.set_valign(Gtk.Align.CENTER)
        cmd_lbl.set_selectable(True)
        cmd_row.add_suffix(cmd_lbl)
        copy_btn = Gtk.Button.new_from_icon_name("edit-copy-symbolic")
        copy_btn.set_tooltip_text("Copiar comando")
        copy_btn.add_css_class("flat")
        copy_btn.set_valign(Gtk.Align.CENTER)
        copy_btn.connect("clicked", self._on_copy)
        cmd_row.add_suffix(copy_btn)
        cmd_row.add_css_class("property")
        self._term_group.add(cmd_row)

        # ---- Atualizacoes disponiveis: SEPARADAS por origem ----
        # Sistema (pacotes do SO) vs Programas da suite Vigia (catalogo/vigia-*),
        # pra deixar claro o que sera atualizado.
        self._system_group = Adw.PreferencesGroup()
        self._system_group.set_title("Sistema")
        self._system_group.set_description(
            "Pacotes do sistema operacional com atualização."
        )
        self._system_group.set_margin_top(8)
        self._system_group.set_visible(False)

        self._suite_group = Adw.PreferencesGroup()
        self._suite_group.set_title("Programas da suíte Vigia")
        self._suite_group.set_description(
            "Ferramentas instaladas pela Vigia (lynis, clamav, …) com atualização."
        )
        self._suite_group.set_margin_top(8)
        self._suite_group.set_visible(False)

        # ---- Layout ----
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        outer.set_margin_top(0)
        outer.set_margin_bottom(32)
        outer.set_margin_start(28)
        outer.set_margin_end(28)
        outer.append(self._hero)
        outer.append(self._hero_sub)
        outer.append(action_box)
        outer.append(self._term_group)
        outer.append(self._system_group)
        outer.append(self._suite_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))

        self._toaster = Adw.ToastOverlay()
        self._toaster.set_child(scrolled)
        self.set_child(self._toaster)

        self.recheck()

    # ============================================================
    # Checagem (async)
    # ============================================================

    def recheck(self) -> None:
        if self._working:
            return
        self._set_working(True, "Verificando atualizações…")
        threading.Thread(target=self._check_worker, daemon=True).start()

    def _check_worker(self) -> None:
        try:
            info = backend.check_updates()
        except Exception:  # pylint: disable=broad-except
            info = backend.UpdateInfo(error="Falha inesperada na checagem.")
        GLib.idle_add(self._apply, info)

    def _apply(self, info: "backend.UpdateInfo") -> bool:
        self._set_working(False)
        for cls in ("success", "warning", "dim-label"):
            self._hero.remove_css_class(cls)

        if not info.checked:
            self._hero.set_label("Não foi possível checar")
            self._hero.add_css_class("warning")
            self._hero_sub.set_label(
                info.error or "Tente novamente em instantes."
            )
            self._update_btn.set_sensitive(False)
        elif info.available:
            suite, system = backend.split_updates(info.packages)
            n = len(info.packages)
            self._hero.set_label("Atualizações disponíveis")
            self._hero.add_css_class("warning")
            if n:
                parts = []
                if system:
                    parts.append(f"{len(system)} do sistema")
                if suite:
                    parts.append(f"{len(suite)} da suíte")
                self._hero_sub.set_label(" · ".join(parts) + ".")
            else:
                self._hero_sub.set_label("Há atualização do sistema disponível.")
            self._update_btn.set_sensitive(True)
        else:
            self._hero.set_label("Sistema atualizado")
            self._hero.add_css_class("success")
            self._hero_sub.set_label("Nenhuma atualização pendente. Tudo em dia.")
            self._update_btn.set_sensitive(False)

        self._render_available(info)
        return False  # idle_add: nao repete

    # ============================================================
    # Render das listas
    # ============================================================

    def _clear_dyn(self) -> None:
        for row in self._dyn_rows:
            parent = row.get_parent()
            if parent is not None and hasattr(parent, "remove"):
                try:
                    parent.remove(row)
                except Exception:  # pylint: disable=broad-except
                    pass
        self._dyn_rows = []

    def _render_available(self, info: "backend.UpdateInfo") -> None:
        self._clear_dyn()
        if not (info.checked and info.available):
            self._system_group.set_visible(False)
            self._suite_group.set_visible(False)
            return

        suite, system = backend.split_updates(info.packages)

        # Sistema
        if system:
            self._system_group.set_visible(True)
            for pkg in system:
                self._system_group.add(self._pkg_row(pkg, suite=False))
        elif not info.packages:
            # Defensivo: update disponivel mas sem lista pacote-a-pacote.
            self._system_group.set_visible(True)
            row = Adw.ActionRow()
            row.set_title("Atualização do sistema")
            row.set_subtitle("Há atualizações disponíveis para baixar.")
            row.add_prefix(
                Gtk.Image.new_from_icon_name("software-update-available-symbolic")
            )
            self._system_group.add(row)
            self._dyn_rows.append(row)
        else:
            self._system_group.set_visible(False)

        # Programas da suite Vigia
        if suite:
            self._suite_group.set_visible(True)
            for pkg in suite:
                self._suite_group.add(self._pkg_row(pkg, suite=True))
        else:
            self._suite_group.set_visible(False)

    def _pkg_row(self, package: str, suite: bool) -> Adw.ActionRow:
        entry = find_by_package(package)
        row = Adw.ActionRow()
        if entry is not None:
            row.set_title(entry.name)
            row.set_subtitle(package)
        else:
            row.set_title(package)
            row.set_subtitle(
                "programa da suíte Vigia" if suite else "pacote do sistema"
            )
        row.add_prefix(
            Gtk.Image.new_from_icon_name("software-update-available-symbolic")
        )
        badge = Gtk.Label(label="ATUALIZAR")
        badge.add_css_class("caption-heading")
        badge.add_css_class("warning")
        badge.set_valign(Gtk.Align.CENTER)
        row.add_suffix(badge)
        self._dyn_rows.append(row)
        return row

    # ============================================================
    # Acoes
    # ============================================================

    def _on_copy(self, _btn: Gtk.Button) -> None:
        copy_to_clipboard(self, backend.update_command_display())
        self._toast("Comando copiado. Cole no terminal e rode.")

    def _toast(self, msg: str) -> None:
        self._toaster.add_toast(Adw.Toast.new(msg))

    def _on_update_now(self, _btn: Gtk.Button) -> None:
        dlg = Adw.AlertDialog(
            heading="Atualizar o sistema agora?",
            body=(
                "O sistema vai baixar e instalar as atualizações agora (dnf). "
                "Pode levar vários minutos — não feche o Hub durante o processo."
            ),
        )
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("go", "Atualizar agora")
        dlg.set_response_appearance("go", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("cancel")
        dlg.connect("response", self._on_update_confirmed)
        dlg.present(self.get_root())

    def _on_update_confirmed(self, _dlg, response: str) -> None:
        if response != "go":
            return
        self._set_working(True, "Atualizando… isso pode levar vários minutos.")
        threading.Thread(target=self._update_worker, daemon=True).start()

    def _update_worker(self) -> None:
        ok, out = backend.run_system_update_blocking()
        GLib.idle_add(self._on_update_finished, ok, out)

    def _on_update_finished(self, ok: bool, out: str) -> bool:
        self._set_working(False)
        if ok:
            self._toast("Sistema atualizado com sucesso.")
        else:
            show_error(self, "Falha na atualização", out)
        self.recheck()  # refresca hero/listas/botões em qualquer caso
        return False

    # ============================================================
    # Estado de trabalho
    # ============================================================

    def _set_working(self, working: bool, label: str = "") -> None:
        self._working = working
        self._check_btn.set_sensitive(not working)
        if working:
            # Trabalhando: trava os dois botoes e mostra estado no hero.
            self._update_btn.set_sensitive(False)
            for cls in ("success", "warning", "dim-label"):
                self._hero.remove_css_class(cls)
            self._hero.add_css_class("dim-label")
            self._hero.set_label(label or "Trabalhando…")
            self._hero_sub.set_label("")
        # Quando working=False, quem decide o botao "Atualizar agora" e' o
        # _apply() (depende de haver update disponivel).
