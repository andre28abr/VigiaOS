"""Tab Sobre: explica o AIDE + paths monitorados (read-only). Aba didatica."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .. import backend


ABOUT_TEXT = (
    "<b>AIDE</b> (<i>Advanced Intrusion Detection Environment</i>) calcula um "
    "<i>snapshot</i> dos arquivos do sistema — permissões, owner, mtime, tamanho "
    "e hash <tt>SHA256</tt> de cada arquivo monitorado.\n\n"
    "Esse snapshot inicial é o <b>baseline</b>. A partir dele, qualquer "
    "verificação posterior compara o estado atual com o baseline e reporta "
    "<b>diferenças</b> — arquivos novos, removidos ou modificados.\n\n"
    "<b>Quando há alarme?</b>\n"
    "- Cron job suspeito em <tt>/etc/cron.daily/</tt> → entrada nova, <i>alarme</i>.\n"
    "- <tt>/etc/passwd</tt> editado para criar conta — hash diverge, <i>alarme</i>.\n"
    "- Backdoor em <tt>/root/.ssh/authorized_keys</tt> — hash diverge, <i>alarme</i>.\n\n"
    "<b>Quando não há alarme?</b>\n"
    "- Updates legítimos do sistema. Após <tt>rpm-ostree upgrade</tt>, você verifica "
    "→ vê as mudanças em <tt>/etc</tt> → valida → clica em <b>Re-baseline</b>.\n\n"
    "<b>Boa prática</b>: verificar 1x por dia (via cron/systemd) e re-baselinear "
    "após cada update intencional."
)


class AboutTab(Adw.Bin):
    def __init__(self) -> None:
        super().__init__()
        self._path_rows: list = []

        # About card
        about_group = Adw.PreferencesGroup()
        about_group.set_title("Como funciona")
        about_group.add(self._wrap_markup_in_row(ABOUT_TEXT))

        # System info
        sys_group = Adw.PreferencesGroup()
        sys_group.set_title("Sistema")

        self._installed_lbl = Gtk.Label()
        self._installed_lbl.add_css_class("monospace")
        installed_row = Adw.ActionRow(title="aide instalado")
        installed_row.add_css_class("property")
        installed_row.add_suffix(self._installed_lbl)
        sys_group.add(installed_row)

        self._conf_lbl = Gtk.Label()
        self._conf_lbl.add_css_class("monospace")
        self._conf_row = Adw.ActionRow()
        self._conf_row.add_css_class("property")
        self._conf_row.add_suffix(self._conf_lbl)
        sys_group.add(self._conf_row)

        self._db_lbl = Gtk.Label()
        self._db_lbl.add_css_class("monospace")
        self._db_row = Adw.ActionRow()
        self._db_row.add_css_class("property")
        self._db_row.add_suffix(self._db_lbl)
        sys_group.add(self._db_row)

        # Watched paths
        self._paths_group = Adw.PreferencesGroup()
        self._paths_group.set_title("Caminhos monitorados")
        self._paths_group.set_description(
            "Extraído do config do perfil ativo."
        )

        # Layout
        page = Adw.PreferencesPage()
        page.add(about_group)
        page.add(sys_group)
        page.add(self._paths_group)
        self.set_child(page)

        self.refresh()

    def _wrap_markup_in_row(self, markup: str) -> Adw.PreferencesRow:
        label = Gtk.Label()
        label.set_markup(markup)
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
        return row

    def refresh(self) -> None:
        conf_path = str(backend.active_conf_path())
        db_path = str(backend.active_db_path())
        installed = backend.aide_installed()

        # System info
        self._installed_lbl.set_label("Sim" if installed else "Nao")
        for cls in ("success", "error", "warning"):
            self._installed_lbl.remove_css_class(cls)
        self._installed_lbl.add_css_class("success" if installed else "error")

        self._conf_row.set_title(conf_path)
        conf_ok = backend.aide_conf_exists()
        self._conf_lbl.set_label("Existe" if conf_ok else "Faltando")
        for cls in ("success", "error", "warning"):
            self._conf_lbl.remove_css_class(cls)
        self._conf_lbl.add_css_class("success" if conf_ok else "warning")

        self._db_row.set_title(db_path)
        db_ok = backend.baseline_exists()
        self._db_lbl.set_label("Existe" if db_ok else "Sem baseline")
        for cls in ("success", "error", "warning"):
            self._db_lbl.remove_css_class(cls)
        self._db_lbl.add_css_class("success" if db_ok else "warning")

        # Paths
        for r in self._path_rows:
            self._paths_group.remove(r)
        self._path_rows = []

        paths = backend.parse_conf_watched_paths()
        if not paths:
            row = Adw.ActionRow(title="Nenhum path detectado")
            row.set_subtitle(
                f"Verifique se {conf_path} existe e tem entradas válidas."
            )
            self._paths_group.add(row)
            self._path_rows.append(row)
        else:
            shown = paths[:50]
            for p in shown:
                row = Adw.ActionRow()
                row.set_title(p)
                row.set_use_markup(False)
                self._paths_group.add(row)
                self._path_rows.append(row)

            if len(paths) > 50:
                row = Adw.ActionRow(title=f"… e mais {len(paths) - 50} entradas")
                row.add_css_class("dim-label")
                self._paths_group.add(row)
                self._path_rows.append(row)
