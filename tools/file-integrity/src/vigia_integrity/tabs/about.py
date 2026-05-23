"""Tab Sobre: explica o AIDE e mostra paths monitorados."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .. import backend
from ._helpers import make_clamp


ABOUT_TEXT = (
    "<b>AIDE</b> (<i>Advanced Intrusion Detection Environment</i>) calcula um "
    "<i>snapshot</i> dos arquivos do sistema — permissoes, owner, mtime, tamanho "
    "e hash <tt>SHA256</tt> de cada arquivo monitorado.\n\n"
    "Esse snapshot inicial e' o <b>baseline</b>. A partir dele, qualquer "
    "verificacao posterior compara o estado atual com o baseline e reporta "
    "<b>diferencas</b> — arquivos novos, removidos ou modificados.\n\n"
    "<b>Quando ha alarme?</b>\n"
    "- Atacante substituiu <tt>/usr/sbin/sshd</tt> por um backdoor → "
    "hash divergente, <i>alarme</i>.\n"
    "- Alguem adicionou um cron-job em <tt>/etc/cron.daily/</tt> → "
    "entrada nova, <i>alarme</i>.\n"
    "- <tt>/etc/passwd</tt> foi editado para criar conta — mtime e hash "
    "divergem, <i>alarme</i>.\n\n"
    "<b>Quando nao ha alarme?</b>\n"
    "- Updates legitimos do sistema (<tt>rpm-ostree upgrade</tt>) mudam binarios "
    "<i>por design</i>. Apos um update, voce verifica → ve as mudancas → "
    "valida que sao do update → clica em <b>Re-baseline</b> para aceitar.\n\n"
    "<b>Boa pratica</b>: rodar <i>verificar</i> 1x por dia (via cron/systemd) "
    "e re-baselinear apos cada update intencional."
)


class AboutTab(Adw.Bin):
    def __init__(self) -> None:
        super().__init__()

        # ---- About card ---- #
        about_group = Adw.PreferencesGroup()
        about_group.set_title("Como funciona")

        about_label = Gtk.Label()
        about_label.set_markup(ABOUT_TEXT)
        about_label.set_wrap(True)
        about_label.set_xalign(0)
        about_label.set_selectable(True)
        about_label.set_margin_start(12)
        about_label.set_margin_end(12)
        about_label.set_margin_top(12)
        about_label.set_margin_bottom(12)

        about_row = Adw.PreferencesRow()
        about_row.set_child(about_label)
        about_row.set_activatable(False)
        about_group.add(about_row)

        # ---- Watched paths ---- #
        self._paths_group = Adw.PreferencesGroup()
        self._paths_group.set_title("Caminhos monitorados")
        self._paths_group.set_description(
            "Extraido de /etc/aide.conf. Para customizar, edite o arquivo "
            "(precisa root)."
        )

        # ---- System info ---- #
        sys_group = Adw.PreferencesGroup()
        sys_group.set_title("Sistema")

        installed_row = Adw.ActionRow(title="aide instalado")
        installed_row.add_css_class("property")
        installed_lbl = Gtk.Label(
            label="Sim" if backend.aide_installed() else "Nao"
        )
        installed_lbl.add_css_class("monospace")
        installed_lbl.add_css_class("success" if backend.aide_installed() else "error")
        installed_row.add_suffix(installed_lbl)
        sys_group.add(installed_row)

        conf_row = Adw.ActionRow(title="/etc/aide.conf")
        conf_row.add_css_class("property")
        conf_lbl = Gtk.Label(
            label="Existe" if backend.aide_conf_exists() else "Faltando"
        )
        conf_lbl.add_css_class("monospace")
        conf_lbl.add_css_class("success" if backend.aide_conf_exists() else "warning")
        conf_row.add_suffix(conf_lbl)
        sys_group.add(conf_row)

        db_row = Adw.ActionRow(title="/var/lib/aide/aide.db.gz")
        db_row.add_css_class("property")
        db_lbl = Gtk.Label(
            label="Existe" if backend.baseline_exists() else "Sem baseline"
        )
        db_lbl.add_css_class("monospace")
        db_lbl.add_css_class("success" if backend.baseline_exists() else "warning")
        db_row.add_suffix(db_lbl)
        sys_group.add(db_row)

        # ---- Layout ---- #
        page = Adw.PreferencesPage()
        page.add(about_group)
        page.add(sys_group)
        page.add(self._paths_group)
        self.set_child(page)

        self.refresh()

    def refresh(self) -> None:
        # Limpa paths_group
        child = self._paths_group.get_first_child()
        # Adw.PreferencesGroup nao expoe remove individual facilmente;
        # vamos limpar destruindo e recriando rows. Usamos um truque:
        # mantemos uma lista interna.
        for r in getattr(self, "_path_rows", []):
            self._paths_group.remove(r)
        self._path_rows = []

        paths = backend.parse_conf_watched_paths()
        if not paths:
            row = Adw.ActionRow(title="Nenhum path detectado")
            row.set_subtitle("Verifique se /etc/aide.conf existe e tem entradas validas.")
            self._paths_group.add(row)
            self._path_rows.append(row)
            return

        # Limita a 50 entries pra UI nao explodir
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
