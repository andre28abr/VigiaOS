"""Tab Extensoes de Navegador — v0.4.

Catalogo curado de extensoes open source pra navegadores. Como nao da
pra instalar extensoes via CLI, o app:

1. Detecta browsers instalados (Firefox, Chrome, Chromium, Brave, etc.)
2. Mostra catalogo agrupado por categoria (ad-blocker, anti-tracking, etc.)
3. Botoes 'Abrir no Firefox' / 'Abrir no Chrome' — xdg-open na URL AMO/Web Store
4. State local de marcacao: 'instalei via Vigia'
5. Restricao: ad-blocker so 1 marcado por browser por vez (conflito).
   Dialog 'substituir uBlock por AdGuard?'.
"""

from __future__ import annotations

import re
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import browser_extensions as be
from ._helpers import make_clamp, show_error, show_info


def _md_to_pango(md: str) -> str:
    s = md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"`([^`]+)`", r"<tt>\1</tt>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<i>\1</i>", s)
    return s


HEADER_DESC = (
    "Extensões <b>open source</b> recomendadas pra privacidade no navegador. "
    "Bloqueio de ads e tracking funciona melhor aqui do que via DNS — "
    "extensões escondem o elemento (sem buraco no layout) e têm regras "
    "atualizadas.\n\n"
    "Como a instalação real é feita pelo próprio navegador, ao clicar "
    "<i>Abrir no Firefox</i> ou <i>Abrir no Chrome</i> a página da extensão "
    "abre automaticamente — você confirma com 1 clique lá dentro."
)


class ExtensionsTab(Adw.Bin):
    """Catalogo de extensoes + state de marcacao."""

    def __init__(self) -> None:
        super().__init__()
        self._browsers: list[be.BrowserInfo] = []
        self._ext_rows: dict[str, dict] = {}  # ext_id -> {row, browsers_box}

        # ===== Header =====
        header_lbl = Gtk.Label(label="Extensões de Navegador")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(8)

        header_desc = Gtk.Label()
        header_desc.set_markup(HEADER_DESC)
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(20)

        # ===== Banner se nenhum browser instalado =====
        self._no_browser_banner = Adw.Banner()
        self._no_browser_banner.set_revealed(False)

        # ===== Detected browsers =====
        self._browsers_group = Adw.PreferencesGroup()
        self._browsers_group.set_title("Navegadores detectados")
        self._browsers_group.set_description(
            "Os botões abaixo respeitam estes navegadores."
        )

        # ===== Extensions list — agrupada por categoria =====
        self._categories_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=20,
        )
        self._categories_box.set_margin_top(8)

        # ===== Layout =====
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_top(24)
        inner.set_margin_bottom(32)
        inner.set_margin_start(28)
        inner.set_margin_end(28)
        inner.append(header_lbl)
        inner.append(header_desc)
        inner.append(self._browsers_group)
        inner.append(self._categories_box)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.append(self._no_browser_banner)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(inner))
        outer.append(scrolled)
        self.set_child(outer)

        self.refresh()

    # ============================================================
    # Refresh
    # ============================================================

    def refresh(self) -> None:
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        try:
            browsers = be.detect_installed_browsers()
        except Exception as e:  # pylint: disable=broad-except
            print(f"[extensions] detect falhou: {e}", flush=True)
            browsers = []
        GLib.idle_add(self._apply, browsers)

    def _apply(self, browsers: list[be.BrowserInfo]) -> bool:
        self._browsers = browsers

        # Banner
        if not browsers:
            self._no_browser_banner.set_title(
                "Nenhum navegador detectado (firefox, chrome, brave, etc.)."
            )
            self._no_browser_banner.set_revealed(True)
        else:
            self._no_browser_banner.set_revealed(False)

        # Browsers detectados
        for child in list(self._browsers_group):
            self._browsers_group.remove(child)
        if not browsers:
            row = Adw.ActionRow(title="Nenhum navegador instalado")
            row.add_css_class("dim-label")
            self._browsers_group.add(row)
        else:
            for b in browsers:
                row = Adw.ActionRow(title=b.label)
                row.add_css_class("property")
                row.set_subtitle(f"família: {b.family}")
                self._browsers_group.add(row)

        # Categorias
        for child in list(self._categories_box):
            self._categories_box.remove(child)
        self._ext_rows = {}

        # Agrupa catalogo por categoria
        by_cat: dict[str, list[be.BrowserExtension]] = {}
        for ext in be.CATALOG:
            by_cat.setdefault(ext.category, []).append(ext)

        # Renderiza na ordem de CATEGORY_LABELS (consistencia)
        category_order = list(be.CATEGORY_LABELS.keys())
        for cat in category_order:
            if cat not in by_cat:
                continue
            group = self._build_category_group(cat, by_cat[cat])
            self._categories_box.append(group)

        return False

    def _build_category_group(
        self, cat: str, extensions: list[be.BrowserExtension],
    ) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup()
        group.set_title(be.CATEGORY_LABELS.get(cat, cat))
        if cat in be.EXCLUSIVE_CATEGORIES:
            group.set_description(
                "Use apenas UM destes por navegador — eles conflitam se "
                "ativos ao mesmo tempo (regras duplicadas, performance ruim)."
            )

        for ext in extensions:
            row = self._build_extension_row(ext)
            group.add(row)
            self._ext_rows[ext.id] = {"row": row}
        return group

    def _build_extension_row(
        self, ext: be.BrowserExtension,
    ) -> Adw.ExpanderRow:
        row = Adw.ExpanderRow()
        title = ext.name
        if ext.recommended:
            title = f"{title}  ★"
        row.set_title(title)
        row.set_subtitle(ext.description)

        # Badges (license + recommended)
        badges = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        badges.set_valign(Gtk.Align.CENTER)
        lic = Gtk.Label(label=ext.license)
        lic.add_css_class("caption")
        lic.add_css_class("dim-label")
        badges.append(lic)
        row.add_prefix(badges)

        # Why (paragrafo)
        why_label = Gtk.Label()
        why_label.set_markup(_md_to_pango(ext.why))
        why_label.set_wrap(True)
        why_label.set_xalign(0)
        why_label.set_selectable(True)
        why_label.set_margin_start(12)
        why_label.set_margin_end(12)
        why_label.set_margin_top(8)
        why_label.set_margin_bottom(12)
        why_row = Adw.PreferencesRow()
        why_row.set_child(why_label)
        why_row.set_activatable(False)
        row.add_row(why_row)

        # Homepage row
        homepage_row = Adw.ActionRow(title="Projeto")
        homepage_row.add_css_class("property")
        homepage_row.set_subtitle(ext.homepage)
        row.add_row(homepage_row)

        # Botoes — 1 row por browser instalado
        for browser in self._browsers:
            url = be.url_for(ext, browser)
            if url is None:
                # Extensao nao disponivel na store deste browser — pula
                continue
            b_row = self._build_browser_action_row(ext, browser)
            row.add_row(b_row)

        return row

    def _build_browser_action_row(
        self, ext: be.BrowserExtension, browser: be.BrowserInfo,
    ) -> Adw.ActionRow:
        b_row = Adw.ActionRow(title=browser.label)
        b_row.set_subtitle("Abre a página oficial da extensão")

        marked = be.is_marked_installed(ext.id, browser.id)

        # Status indicator (esquerda)
        indicator = Gtk.Label(label="✓ Instalado" if marked else "")
        indicator.add_css_class("caption")
        if marked:
            indicator.add_css_class("success")
        b_row.add_prefix(indicator)

        # Botoes (direita)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.set_valign(Gtk.Align.CENTER)

        open_btn = Gtk.Button(label="Abrir")
        open_btn.add_css_class("flat")
        open_btn.set_tooltip_text(f"Abre AMO/Web Store em {browser.label}")
        open_btn.connect("clicked", self._on_open_clicked, ext, browser)
        box.append(open_btn)

        if marked:
            mark_btn = Gtk.Button(label="Desmarcar")
            mark_btn.add_css_class("destructive-action")
        else:
            mark_btn = Gtk.Button(label="Marcar instalada")
            mark_btn.add_css_class("suggested-action")
        mark_btn.connect("clicked", self._on_mark_clicked, ext, browser)
        box.append(mark_btn)

        b_row.add_suffix(box)
        return b_row

    # ============================================================
    # Acoes
    # ============================================================

    def _on_open_clicked(
        self, _btn, ext: be.BrowserExtension, browser: be.BrowserInfo,
    ) -> None:
        ok, err = be.open_in_browser(ext, browser)
        if not ok:
            show_error(self, "Falha ao abrir", err)

    def _on_mark_clicked(
        self, _btn, ext: be.BrowserExtension, browser: be.BrowserInfo,
    ) -> None:
        if be.is_marked_installed(ext.id, browser.id):
            # Toggle off
            be.unmark_installed(ext.id, browser.id)
            self.refresh()
            return

        # Check conflicts (mesma categoria, mesmo browser)
        conflicts = be.find_conflicts(ext.id, browser.id)
        if conflicts:
            self._show_conflict_dialog(ext, browser, conflicts)
            return

        # Sem conflito — marca direto
        be.mark_installed(ext.id, browser.id)
        show_info(
            self,
            f"{ext.name} marcada",
            f"Marcada como instalada em {browser.label}. Se você ainda "
            f"não instalou, clique em 'Abrir' pra ir pra página oficial.",
        )
        self.refresh()

    def _show_conflict_dialog(
        self, ext: be.BrowserExtension, browser: be.BrowserInfo,
        conflicts: list[str],
    ) -> None:
        conflict_names = []
        for cid in conflicts:
            other = be.find_extension(cid)
            if other:
                conflict_names.append(other.name)
        conflict_str = ", ".join(conflict_names)

        cat_label = be.CATEGORY_LABELS.get(ext.category, ext.category)

        dlg = Adw.AlertDialog(
            heading=f"Substituir {conflict_str}?",
            body=(
                f"Você já marcou <b>{conflict_str}</b> como instalada em "
                f"<b>{browser.label}</b>.\n\n"
                f"Categoria <b>{cat_label}</b> deve ter apenas 1 extensão "
                f"ativa por vez (conflito de regras causa performance ruim "
                f"e bugs).\n\n"
                f"Recomendamos:\n"
                f"1. <b>Desinstalar {conflict_str} no {browser.label}</b> "
                f"(pelo menu de extensões do navegador)\n"
                f"2. Confirmar abaixo pra trocar a marcação no Vigia\n"
                f"3. Clicar 'Abrir' pra instalar <b>{ext.name}</b>"
            ),
        )
        dlg.set_body_use_markup(True)
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("swap", f"Trocar pra {ext.name}")
        dlg.set_response_appearance("swap", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("cancel")
        dlg.connect("response", self._on_conflict_response, ext, browser, conflicts)
        dlg.present(self.get_root())

    def _on_conflict_response(
        self, _dlg, response: str,
        ext: be.BrowserExtension, browser: be.BrowserInfo,
        conflicts: list[str],
    ) -> None:
        if response != "swap":
            return
        # Desmarca conflitantes
        for cid in conflicts:
            be.unmark_installed(cid, browser.id)
        # Marca nova
        be.mark_installed(ext.id, browser.id)
        show_info(
            self,
            f"{ext.name} marcada",
            f"Conflitantes desmarcadas. Clique 'Abrir' pra instalar "
            f"{ext.name} no {browser.label}, e não esqueça de DESINSTALAR "
            f"as anteriores pelo menu do navegador.",
        )
        self.refresh()
