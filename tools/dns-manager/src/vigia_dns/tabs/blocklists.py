"""Tab Blocklists (v0.2 — modo avancado dnscrypt-proxy).

Gerencia /etc/dnscrypt-proxy/blacklist.txt:
- Lista dominios bloqueados
- Add/remove individual
- Importar de URL (formato hosts ou domain-per-line)

Mostra empty state com instrucao se modo avancado nao esta ativo.
"""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import dnscrypt_backend as dc
from .. import migration
from ._helpers import make_clamp, show_error, show_info


# Listas publicas conhecidas (sugestoes em quick-pick)
SUGGESTED_LISTS = [
    {
        "name": "StevenBlack hosts (ads + malware)",
        "url": "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts",
        "size": "~200k entries",
    },
    {
        "name": "EasyList (anti-tracking)",
        "url": "https://easylist.to/easylist/easyprivacy.txt",
        "size": "~50k entries",
    },
    {
        "name": "OISD (NSFW + malware, escolha small)",
        "url": "https://small.oisd.nl/",
        "size": "~150k entries",
    },
]


class BlocklistsTab(Adw.Bin):
    """UI para gerenciar blocklist do dnscrypt-proxy."""

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._domains: list[str] = []

        # ===== Header =====
        header_lbl = Gtk.Label(label="Blocklist de dominios")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(8)

        header_desc = Gtk.Label(
            label=(
                "Lista de <b>dominios bloqueados</b> pelo dnscrypt-proxy. "
                "Queries que batem na lista retornam NXDOMAIN — sites/apps "
                "que dependem deles falham (efeito Pi-hole).\n\n"
                "Util para bloquear tracking corporate e ads de marketing "
                "no escritorio sem instalar Pi-hole em hardware separado.\n\n"
                "Arquivo: <tt>/etc/dnscrypt-proxy/blacklist.txt</tt>"
            )
        )
        header_desc.set_use_markup(True)
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(24)

        # ===== Banner se modo avancado nao esta ativo =====
        self._mode_banner = Adw.Banner()
        self._mode_banner.set_revealed(False)

        # ===== Add manual =====
        add_group = Adw.PreferencesGroup()
        add_group.set_title("Adicionar dominio manualmente")
        add_group.set_description(
            "Bloqueia um dominio especifico. Aceita wildcard (*.exemplo.com)."
        )

        self._add_entry = Gtk.Entry()
        self._add_entry.set_placeholder_text("ex: doubleclick.net")
        self._add_entry.set_hexpand(True)
        add_row = Adw.ActionRow(title="Dominio")
        add_row.add_suffix(self._add_entry)
        add_group.add(add_row)

        add_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        add_btn_box.set_halign(Gtk.Align.END)
        add_btn_box.set_margin_top(16)
        self._add_btn = Gtk.Button(label="Adicionar")
        self._add_btn.add_css_class("suggested-action")
        self._add_btn.connect("clicked", lambda _b: self._do_add())
        add_btn_box.append(self._add_btn)

        # ===== Import de URL =====
        import_group = Adw.PreferencesGroup()
        import_group.set_margin_top(28)
        import_group.set_title("Importar de URL")
        import_group.set_description(
            "Baixa lista publica (formato hosts ou domain-per-line). "
            "Acrescenta a lista atual (sem duplicar)."
        )

        self._url_entry = Gtk.Entry()
        self._url_entry.set_placeholder_text("https://...")
        self._url_entry.set_hexpand(True)
        url_row = Adw.ActionRow(title="URL")
        url_row.add_suffix(self._url_entry)
        import_group.add(url_row)

        # Sugestoes pré-prontas (chips)
        chips_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        chips_box.set_margin_top(8)
        chips_box.set_margin_bottom(8)
        chips_box.set_margin_start(12)
        chips_box.set_margin_end(12)
        chips_label = Gtk.Label(label="Listas sugeridas (clique para preencher URL):")
        chips_label.add_css_class("caption")
        chips_label.add_css_class("dim-label")
        chips_label.set_halign(Gtk.Align.START)
        chips_box.append(chips_label)

        chips_flow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        for sug in SUGGESTED_LISTS:
            btn = Gtk.Button(label=sug["name"])
            btn.add_css_class("pill")
            btn.add_css_class("flat")
            btn.set_tooltip_text(f"{sug['url']}\n{sug['size']}")
            btn.connect("clicked", lambda _b, u=sug["url"]: self._url_entry.set_text(u))
            chips_flow.append(btn)
        chips_box.append(chips_flow)

        chips_row = Adw.PreferencesRow()
        chips_row.set_child(chips_box)
        chips_row.set_activatable(False)
        import_group.add(chips_row)

        import_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        import_btn_box.set_halign(Gtk.Align.END)
        import_btn_box.set_margin_top(16)
        self._import_spinner = Gtk.Spinner()
        import_btn_box.append(self._import_spinner)
        self._import_btn = Gtk.Button(label="Importar")
        self._import_btn.add_css_class("suggested-action")
        self._import_btn.connect("clicked", lambda _b: self._do_import())
        import_btn_box.append(self._import_btn)

        # ===== Lista atual =====
        self._list_group = Adw.PreferencesGroup()
        self._list_group.set_margin_top(28)
        self._list_group.set_title("Dominios bloqueados")
        self._list_group.set_description("0 dominios na blocklist atual.")
        self._list_rows: list = []

        # Status label
        self._status_label = Gtk.Label(label="")
        self._status_label.add_css_class("dim-label")
        self._status_label.set_halign(Gtk.Align.START)
        self._status_label.set_wrap(True)
        self._status_label.set_xalign(0)

        # ===== Layout =====
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_top(24)
        inner.set_margin_bottom(32)
        inner.set_margin_start(28)
        inner.set_margin_end(28)
        inner.append(header_lbl)
        inner.append(header_desc)
        inner.append(add_group)
        inner.append(add_btn_box)
        inner.append(import_group)
        inner.append(import_btn_box)
        inner.append(self._status_label)
        inner.append(self._list_group)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.append(self._mode_banner)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(inner))
        outer.append(scrolled)

        self.set_child(outer)

        # Carrega estado inicial
        self.refresh()

    # ============================================================
    # Refresh
    # ============================================================

    def refresh(self) -> None:
        """Recarrega blocklist + verifica modo ativo."""
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        installed = dc.dnscrypt_installed()
        mode = migration.get_current_mode() if installed else "unknown"
        domains = dc.get_blocklist() if installed else []
        GLib.idle_add(self._apply, installed, mode, domains)

    def _apply(self, installed: bool, mode: str, domains: list[str]) -> bool:
        # Banner se modo avancado nao esta ativo
        if not installed:
            self._mode_banner.set_title(
                "dnscrypt-proxy nao instalado. Instale via Vigia Tool "
                "Installer para usar blocklists."
            )
            self._mode_banner.set_revealed(True)
            self._set_actions_enabled(False)
        elif mode != "advanced":
            self._mode_banner.set_title(
                "Modo avancado (dnscrypt-proxy) nao esta ativo. Va a aba "
                "Status e ative o switch para gerenciar blocklists."
            )
            self._mode_banner.set_revealed(True)
            self._set_actions_enabled(False)
        else:
            self._mode_banner.set_revealed(False)
            self._set_actions_enabled(True)

        # Domains
        self._domains = domains
        self._list_group.set_description(
            f"{len(domains)} dominio{'s' if len(domains) != 1 else ''} "
            f"na blocklist atual."
        )
        self._render_list()
        return False

    def _set_actions_enabled(self, enabled: bool) -> None:
        self._add_btn.set_sensitive(enabled and not self._running)
        self._import_btn.set_sensitive(enabled and not self._running)
        self._add_entry.set_sensitive(enabled)
        self._url_entry.set_sensitive(enabled)

    # ============================================================
    # Render list
    # ============================================================

    def _render_list(self) -> None:
        for r in self._list_rows:
            self._list_group.remove(r)
        self._list_rows = []

        if not self._domains:
            row = Adw.ActionRow(title="Lista vazia")
            row.set_subtitle(
                "Adicione dominios acima ou importe uma lista publica."
            )
            row.add_css_class("dim-label")
            self._list_group.add(row)
            self._list_rows.append(row)
            return

        # Limita a 100 visiveis (performance + UX)
        shown = self._domains[:100]
        for d in shown:
            row = Adw.ActionRow(title=d)
            row.add_css_class("property")
            del_btn = Gtk.Button.new_from_icon_name("user-trash-symbolic")
            del_btn.add_css_class("flat")
            del_btn.set_tooltip_text(f"Remover {d}")
            del_btn.set_valign(Gtk.Align.CENTER)
            del_btn.connect("clicked", lambda _b, dom=d: self._do_remove(dom))
            row.add_suffix(del_btn)
            self._list_group.add(row)
            self._list_rows.append(row)

        if len(self._domains) > 100:
            more = Adw.ActionRow(
                title=f"... +{len(self._domains) - 100} dominios (mostrando primeiros 100)"
            )
            more.add_css_class("dim-label")
            self._list_group.add(more)
            self._list_rows.append(more)

    # ============================================================
    # Add / Remove / Import
    # ============================================================

    def _do_add(self) -> None:
        if self._running:
            return
        domain = self._add_entry.get_text().strip().lower()
        if not domain:
            show_error(self, "Sem dominio", "Digite um dominio para adicionar.")
            return

        self._running = True
        self._set_actions_enabled(False)
        threading.Thread(target=self._add_worker, args=(domain,), daemon=True).start()

    def _add_worker(self, domain: str) -> None:
        ok, err = dc.add_blocklist_entry(domain)
        # Se acabou de criar a primeira entry, garante que config aponta
        if ok and len(self._domains) == 0:
            dc.enable_blocklist_in_config()
        GLib.idle_add(self._on_add_done, ok, err, domain)

    def _on_add_done(self, ok: bool, err: str, domain: str) -> bool:
        self._running = False
        if not ok:
            show_error(self, "Falha ao adicionar", err)
        else:
            self._add_entry.set_text("")
        self.refresh()
        return False

    def _do_remove(self, domain: str) -> None:
        if self._running:
            return
        self._running = True
        self._set_actions_enabled(False)
        threading.Thread(target=self._remove_worker, args=(domain,), daemon=True).start()

    def _remove_worker(self, domain: str) -> None:
        ok, err = dc.remove_blocklist_entry(domain)
        GLib.idle_add(self._on_remove_done, ok, err)

    def _on_remove_done(self, ok: bool, err: str) -> bool:
        self._running = False
        if not ok:
            show_error(self, "Falha ao remover", err)
        self.refresh()
        return False

    def _do_import(self) -> None:
        if self._running:
            return
        url = self._url_entry.get_text().strip()
        if not url:
            show_error(self, "Sem URL", "Cole uma URL ou escolha uma lista sugerida.")
            return

        self._running = True
        self._set_actions_enabled(False)
        self._import_spinner.start()
        self._status_label.set_label(
            "Baixando lista... pode levar 10-30s dependendo do tamanho."
        )
        threading.Thread(target=self._import_worker, args=(url,), daemon=True).start()

    def _import_worker(self, url: str) -> None:
        ok, added, err = dc.import_blocklist_from_url(url, append=True)
        # Garante que config aponta pra blocklist
        if ok:
            dc.enable_blocklist_in_config()
        GLib.idle_add(self._on_import_done, ok, added, err)

    def _on_import_done(self, ok: bool, added: int, err: str) -> bool:
        self._running = False
        self._import_spinner.stop()
        if not ok:
            self._status_label.set_label(f"Erro: {err}")
            show_error(self, "Falha ao importar", err)
        else:
            self._status_label.set_label(
                f"Importacao concluida: {added} novo(s) dominio(s) adicionado(s)."
            )
            self._url_entry.set_text("")
            show_info(
                self, "Importacao concluida",
                f"{added} novo(s) dominio(s) adicionado(s) a blocklist.",
            )
        self.refresh()
        return False
