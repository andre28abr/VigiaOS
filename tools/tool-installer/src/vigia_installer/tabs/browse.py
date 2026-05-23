"""Tab Catalogo: browse + install."""

from __future__ import annotations

import threading
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from ..catalog import (
    CATALOG,
    CATEGORY_DESCRIPTIONS,
    CATEGORY_LABELS,
    CatalogEntry,
    by_category,
)
from ._helpers import make_clamp, show_error, show_info


# Markdown leve compartilhado — duplicado do hub por enquanto.
import re


def _md_to_pango(md: str) -> str:
    s = md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"`([^`]+)`", r"<tt>\1</tt>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<i>\1</i>", s)
    return s


class BrowseTab(Adw.Bin):
    """Lista categorizada do catalogo com botoes Instalar/Remover por item."""

    def __init__(self, on_changed: Callable[[], None]) -> None:
        super().__init__()
        self._on_changed = on_changed
        self._running = False
        self._row_widgets: dict[str, dict] = {}  # package -> {row, btn, status_lbl}

        # Header
        header_lbl = Gtk.Label(label="Catalogo curado")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(4)

        header_desc = Gtk.Label(
            label=(
                f"{len(CATALOG)} ferramentas de seguranca selecionadas. "
                "Cada install vira uma camada via rpm-ostree e precisa de reboot para aplicar."
            )
        )
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(20)

        # Search
        self._search = Gtk.SearchEntry()
        self._search.set_placeholder_text("Buscar por nome, descricao ou pacote...")
        self._search.set_hexpand(True)
        self._search.connect("search-changed", lambda _e: self._apply_filter())
        self._search.set_margin_bottom(16)

        # Progress (escondido)
        self._progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._progress_box.set_visible(False)
        self._progress_box.set_margin_bottom(16)
        self._progress_label = Gtk.Label(label="Trabalhando...")
        self._progress_label.add_css_class("dim-label")
        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.set_pulse_step(0.1)
        self._progress_box.append(self._progress_label)
        self._progress_box.append(self._progress_bar)

        # Container das categorias
        self._categories_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)

        # Layout
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(20)
        outer.set_margin_bottom(20)
        outer.set_margin_start(20)
        outer.set_margin_end(20)
        outer.append(header_lbl)
        outer.append(header_desc)
        outer.append(self._search)
        outer.append(self._progress_box)
        outer.append(self._categories_box)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

        self._build_catalog()
        self.refresh_statuses()

    # ============================================================
    # Build
    # ============================================================

    def _build_catalog(self) -> None:
        for cat, entries in by_category().items():
            group = Adw.PreferencesGroup()
            group.set_title(CATEGORY_LABELS.get(cat, cat))
            group.set_description(CATEGORY_DESCRIPTIONS.get(cat, ""))

            for e in entries:
                row = self._build_row(e)
                group.add(row["row"])
                self._row_widgets[e.package] = row

            self._categories_box.append(group)

    def _build_row(self, e: CatalogEntry) -> dict:
        row = Adw.ExpanderRow()
        row.set_title(e.name)
        row.set_subtitle(e.description)

        # Status label como prefix (badge tipo)
        status_lbl = Gtk.Label(label="—")
        status_lbl.add_css_class("caption-heading")
        status_lbl.add_css_class("dim-label")
        status_lbl.set_valign(Gtk.Align.CENTER)
        row.add_prefix(status_lbl)

        # Botao acao como suffix
        action_btn = Gtk.Button(label="Instalar")
        action_btn.set_valign(Gtk.Align.CENTER)
        action_btn.add_css_class("suggested-action")
        action_btn.connect("clicked", self._on_action_clicked, e.package)
        row.add_suffix(action_btn)

        # Conteudo expandido: descricao longa
        why_label = Gtk.Label()
        why_label.set_markup(_md_to_pango(e.why))
        why_label.set_wrap(True)
        why_label.set_xalign(0)
        why_label.set_selectable(True)
        why_label.set_margin_start(12)
        why_label.set_margin_end(12)
        why_label.set_margin_top(8)
        why_label.set_margin_bottom(12)

        # Package info row
        pkg_row = Adw.ActionRow()
        pkg_row.set_title("Pacote")
        pkg_lbl = Gtk.Label(label=e.package)
        pkg_lbl.add_css_class("monospace")
        pkg_lbl.set_valign(Gtk.Align.CENTER)
        pkg_row.add_suffix(pkg_lbl)
        pkg_row.add_css_class("property")

        why_row = Adw.PreferencesRow()
        why_row.set_child(why_label)
        why_row.set_activatable(False)

        row.add_row(why_row)
        row.add_row(pkg_row)

        return {
            "row": row,
            "btn": action_btn,
            "status": status_lbl,
            "entry": e,
        }

    # ============================================================
    # Status refresh
    # ============================================================

    def refresh_statuses(self) -> None:
        pending = backend.pending_changes()
        pending_set = set(pending.pending_added)
        pending_removed_set = set(pending.pending_removed)

        for pkg, widgets in self._row_widgets.items():
            installed = backend.is_package_installed(pkg)
            row = widgets["row"]
            status: Gtk.Label = widgets["status"]
            btn: Gtk.Button = widgets["btn"]

            for cls in ("success", "warning", "dim-label", "error"):
                status.remove_css_class(cls)

            if pkg in pending_set and not installed:
                status.set_label("PENDENTE")
                status.add_css_class("warning")
                btn.set_label("Pendente")
                btn.set_sensitive(False)
                btn.remove_css_class("suggested-action")
                btn.remove_css_class("destructive-action")
            elif pkg in pending_removed_set:
                status.set_label("REMOCAO PENDENTE")
                status.add_css_class("warning")
                btn.set_label("Removendo")
                btn.set_sensitive(False)
            elif installed:
                status.set_label("INSTALADO")
                status.add_css_class("success")
                btn.set_label("Remover")
                btn.set_sensitive(not self._running)
                btn.remove_css_class("suggested-action")
                btn.add_css_class("destructive-action")
                btn.add_css_class("flat")
            else:
                status.set_label("Disponivel")
                status.add_css_class("dim-label")
                btn.set_label("Instalar")
                btn.set_sensitive(not self._running)
                btn.add_css_class("suggested-action")
                btn.remove_css_class("destructive-action")
                btn.remove_css_class("flat")

    # ============================================================
    # Filter
    # ============================================================

    def _apply_filter(self) -> None:
        q = self._search.get_text().strip().lower()
        for pkg, widgets in self._row_widgets.items():
            e: CatalogEntry = widgets["entry"]
            visible = True
            if q:
                visible = (
                    q in e.name.lower()
                    or q in e.package.lower()
                    or q in e.description.lower()
                    or q in e.why.lower()
                )
            widgets["row"].set_visible(visible)

    # ============================================================
    # Actions
    # ============================================================

    def _on_action_clicked(self, btn: Gtk.Button, package: str) -> None:
        if self._running:
            return
        installed = backend.is_package_installed(package)
        if installed:
            self._confirm_uninstall(package)
        else:
            self._do_install(package)

    def _confirm_uninstall(self, package: str) -> None:
        entry = self._row_widgets[package]["entry"]
        dlg = Adw.AlertDialog(
            heading=f"Remover {entry.name}?",
            body=(
                f"O pacote `{package}` sera removido na proxima reinicializacao "
                "(rpm-ostree uninstall). Mudanca aplicada com reboot."
            ),
        )
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("remove", "Remover")
        dlg.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("cancel")
        dlg.connect("response", self._on_uninstall_confirmed, package)
        dlg.present(self.get_root())

    def _on_uninstall_confirmed(self, _dlg, response: str, package: str) -> None:
        if response == "remove":
            self._do_uninstall(package)

    def _do_install(self, package: str) -> None:
        self._set_running(True, f"Instalando {package} via rpm-ostree...")
        threading.Thread(target=self._install_worker, args=(package,), daemon=True).start()

    def _install_worker(self, package: str) -> None:
        ok, out = backend.install_packages_blocking([package])
        GLib.idle_add(self._on_install_finished, ok, out, package)

    def _on_install_finished(self, ok: bool, out: str, package: str) -> bool:
        self._set_running(False)
        if not ok:
            show_error(self, f"Falha ao instalar {package}", out)
        else:
            show_info(
                self,
                f"{package}: pronto",
                "Mudanca staged. Para usar, reinicie o sistema (aba 'Pendentes' tem botao Reboot).",
            )
            self.refresh_statuses()
            self._on_changed()
        return False

    def _do_uninstall(self, package: str) -> None:
        self._set_running(True, f"Removendo {package} via rpm-ostree...")
        threading.Thread(target=self._uninstall_worker, args=(package,), daemon=True).start()

    def _uninstall_worker(self, package: str) -> None:
        ok, out = backend.uninstall_packages_blocking([package])
        GLib.idle_add(self._on_uninstall_finished, ok, out, package)

    def _on_uninstall_finished(self, ok: bool, out: str, package: str) -> bool:
        self._set_running(False)
        if not ok:
            show_error(self, f"Falha ao remover {package}", out)
        else:
            show_info(
                self,
                f"{package}: removido (pendente)",
                "Mudanca staged. Reinicie para aplicar.",
            )
            self.refresh_statuses()
            self._on_changed()
        return False

    # ============================================================
    # Progress / running
    # ============================================================

    def _set_running(self, running: bool, label: str = "Trabalhando...") -> None:
        self._running = running
        self._progress_box.set_visible(running)
        self._progress_label.set_label(label)
        if running:
            self._pulse_id = GLib.timeout_add(100, self._pulse_tick)
        else:
            pid = getattr(self, "_pulse_id", None)
            if pid is not None:
                GLib.source_remove(pid)
                self._pulse_id = None
        # Desabilita todos os botoes durante operacao
        for widgets in self._row_widgets.values():
            widgets["btn"].set_sensitive(not running)

    def _pulse_tick(self) -> bool:
        self._progress_bar.pulse()
        return self._running
