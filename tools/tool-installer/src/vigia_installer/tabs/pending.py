"""Tab Pendentes: mudancas staged que precisam reboot."""

from __future__ import annotations

import threading
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from ..catalog import find_by_package
from ._helpers import make_clamp, show_error


class PendingTab(Adw.Bin):
    """Lista pacotes pending + botao Reiniciar."""

    def __init__(self, on_changed: Callable[[], None]) -> None:
        super().__init__()
        self._on_changed = on_changed

        # Header / hero
        self._state_label = Gtk.Label(label="Verificando...")
        self._state_label.add_css_class("title-1")
        self._state_label.set_halign(Gtk.Align.CENTER)
        self._state_label.set_margin_top(32)

        self._state_sub = Gtk.Label(label="")
        self._state_sub.add_css_class("title-4")
        self._state_sub.add_css_class("dim-label")
        self._state_sub.set_halign(Gtk.Align.CENTER)
        self._state_sub.set_wrap(True)
        self._state_sub.set_justify(Gtk.Justification.CENTER)
        self._state_sub.set_max_width_chars(48)
        self._state_sub.set_margin_bottom(24)

        # Action bar
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        action_box.set_halign(Gtk.Align.CENTER)
        action_box.set_margin_bottom(28)

        self._reboot_btn = Gtk.Button(label="Reiniciar agora")
        self._reboot_btn.add_css_class("suggested-action")
        self._reboot_btn.connect("clicked", self._on_reboot_clicked)
        action_box.append(self._reboot_btn)

        self._refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        self._refresh_btn.set_tooltip_text("Atualizar status")
        self._refresh_btn.connect("clicked", lambda _b: self.refresh())
        action_box.append(self._refresh_btn)

        # Groups (added / removed)
        self._added_group = Adw.PreferencesGroup()
        self._added_group.set_title("Sera instalado no proximo boot")

        self._removed_group = Adw.PreferencesGroup()

        self._removed_group.set_margin_top(24)
        self._removed_group.set_title("Sera removido no proximo boot")

        # Current layered
        self._current_group = Adw.PreferencesGroup()
        self._current_group.set_margin_top(24)
        self._current_group.set_title("Atualmente instalados (camada rpm-ostree)")
        self._current_group.set_description(
            "Pacotes que ja estao na camada atual (instalados antes do boot atual)."
        )

        # Layout
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        outer.set_margin_top(0)
        outer.set_margin_bottom(32)
        outer.set_margin_start(28)
        outer.set_margin_end(28)
        outer.append(self._state_label)
        outer.append(self._state_sub)
        outer.append(action_box)
        outer.append(self._added_group)
        outer.append(self._removed_group)
        outer.append(self._current_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

        # tracking de rows para limpeza
        self._row_refs: list[Adw.ActionRow] = []
        self._refresh_id = 0

        self.refresh()

    # ============================================================
    # Refresh (async: subprocess vai pra worker thread)
    # ============================================================

    def refresh(self) -> None:
        """Dispara coleta em thread. UI thread fica livre."""
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        try:
            pending = backend.pending_changes()
        except Exception:  # pylint: disable=broad-except
            pending = backend.PendingChanges()
        GLib.idle_add(self._apply_pending, pending)

    def _apply_pending(self, pending: "backend.PendingChanges") -> bool:
        # Hero
        for cls in ("success", "warning", "dim-label"):
            self._state_label.remove_css_class(cls)

        if pending.has_pending:
            self._state_label.set_label("Mudancas pendentes")
            self._state_label.add_css_class("warning")
            total = len(pending.pending_added) + len(pending.pending_removed)
            self._state_sub.set_label(
                f"{total} pacote{'s' if total > 1 else ''} sera{'o' if total > 1 else ''} aplicado"
                f"{'s' if total > 1 else ''} no proximo boot. Reinicie para concluir."
            )
            self._reboot_btn.set_sensitive(True)
        elif pending.current_layered:
            self._state_label.set_label("Sem mudancas pendentes")
            self._state_label.add_css_class("success")
            self._state_sub.set_label(
                f"{len(pending.current_layered)} pacote{'s' if len(pending.current_layered) > 1 else ''} "
                "ja instalado(s) na camada atual."
            )
            self._reboot_btn.set_sensitive(False)
        else:
            self._state_label.set_label("Sistema base")
            self._state_label.add_css_class("dim-label")
            self._state_sub.set_label("Nenhum pacote layered. Use a aba 'Catalogo' para instalar.")
            self._reboot_btn.set_sensitive(False)

        # Limpa rows antigas
        for ref in self._row_refs:
            parent = ref.get_parent()
            if parent is not None and hasattr(parent, "remove"):
                try:
                    parent.remove(ref)
                except Exception:  # pylint: disable=broad-except
                    pass
        self._row_refs = []

        # Adicionados pendentes
        if pending.pending_added:
            self._added_group.set_visible(True)
            for pkg in pending.pending_added:
                row = self._build_pkg_row(pkg, suffix_text="Sera instalado", css="success")
                self._added_group.add(row)
                self._row_refs.append(row)
        else:
            self._added_group.set_visible(False)

        # Removidos pendentes
        if pending.pending_removed:
            self._removed_group.set_visible(True)
            for pkg in pending.pending_removed:
                row = self._build_pkg_row(pkg, suffix_text="Sera removido", css="error")
                self._removed_group.add(row)
                self._row_refs.append(row)
        else:
            self._removed_group.set_visible(False)

        # Atuais layered
        if pending.current_layered:
            self._current_group.set_visible(True)
            for pkg in pending.current_layered:
                row = self._build_pkg_row(pkg, suffix_text="", css="dim-label")
                self._current_group.add(row)
                self._row_refs.append(row)
        else:
            self._current_group.set_visible(False)

        self._on_changed()
        return False  # GLib.idle_add: nao repete

    def _build_pkg_row(self, package: str, suffix_text: str, css: str) -> Adw.ActionRow:
        entry = find_by_package(package)
        row = Adw.ActionRow()
        if entry is not None:
            row.set_title(entry.name)
            row.set_subtitle(f"{entry.description}  ·  pacote: {package}")
        else:
            row.set_title(package)
            row.set_subtitle("(fora do catalogo Vigia)")

        if suffix_text:
            badge = Gtk.Label(label=suffix_text)
            badge.add_css_class("caption-heading")
            badge.add_css_class(css)
            badge.set_valign(Gtk.Align.CENTER)
            row.add_suffix(badge)

        return row

    # ============================================================
    # Reboot
    # ============================================================

    def _on_reboot_clicked(self, _btn: Gtk.Button) -> None:
        dlg = Adw.AlertDialog(
            heading="Reiniciar agora?",
            body=(
                "O sistema vai reiniciar imediatamente para aplicar as mudancas "
                "pendentes. Salve seu trabalho antes de continuar."
            ),
        )
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("reboot", "Reiniciar agora")
        dlg.set_response_appearance("reboot", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("cancel")
        dlg.connect("response", self._on_reboot_confirmed)
        dlg.present(self.get_root())

    def _on_reboot_confirmed(self, _dlg, response: str) -> None:
        if response != "reboot":
            return
        ok, err = backend.reboot_system()
        if not ok:
            show_error(self, "Falha ao reiniciar", err)
