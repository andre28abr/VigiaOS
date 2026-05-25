"""Tab Sobre: explica o AIDE, mostra paths monitorados e gerencia perfil."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from ._helpers import make_clamp, show_error, show_info


ABOUT_TEXT = (
    "<b>AIDE</b> (<i>Advanced Intrusion Detection Environment</i>) calcula um "
    "<i>snapshot</i> dos arquivos do sistema — permissoes, owner, mtime, tamanho "
    "e hash <tt>SHA256</tt> de cada arquivo monitorado.\n\n"
    "Esse snapshot inicial e' o <b>baseline</b>. A partir dele, qualquer "
    "verificacao posterior compara o estado atual com o baseline e reporta "
    "<b>diferencas</b> — arquivos novos, removidos ou modificados.\n\n"
    "<b>Quando ha alarme?</b>\n"
    "- Cron job suspeito em <tt>/etc/cron.daily/</tt> → entrada nova, <i>alarme</i>.\n"
    "- <tt>/etc/passwd</tt> editado para criar conta — hash diverge, <i>alarme</i>.\n"
    "- Backdoor em <tt>/root/.ssh/authorized_keys</tt> — hash diverge, <i>alarme</i>.\n\n"
    "<b>Quando nao ha alarme?</b>\n"
    "- Updates legitimos do sistema. Apos <tt>rpm-ostree upgrade</tt>, voce verifica "
    "→ ve as mudancas em <tt>/etc</tt> → valida → clica em <b>Re-baseline</b>.\n\n"
    "<b>Boa pratica</b>: verificar 1x por dia (via cron/systemd) e re-baselinear "
    "apos cada update intencional."
)


SILVERBLUE_PROFILE_TEXT = (
    "<b>Por que um perfil dedicado?</b>\n\n"
    "AIDE foi pensado para sistemas tradicionais com <tt>/usr</tt> mutavel. "
    "Em Silverblue, <tt>/usr</tt> e' uma <b>arvore OSTree imutavel</b> — toda "
    "atualizacao do sistema substitui literalmente milhares de arquivos. Se "
    "AIDE monitorasse <tt>/usr</tt>, cada <tt>rpm-ostree upgrade</tt> dispararia "
    "<i>milhares de alarmes</i>, escondendo o que importa.\n\n"
    "A integridade do <tt>/usr</tt> em Silverblue ja e' garantida pelo <b>OSTree "
    "criptografico</b> (verificacao do commit a cada boot).\n\n"
    "O <b>perfil Silverblue (Vigia)</b> usa <tt>/etc/aide-vigia.conf</tt> "
    "(separado do <tt>/etc/aide.conf</tt> do sistema) e foca em:\n"
    "- <tt>/etc</tt> inteiro (sudoers, passwd, shadow, ssh, systemd)\n"
    "- <tt>/root</tt> (.ssh, dotfiles)\n"
    "- <tt>/var/spool/cron</tt>, <tt>/var/spool/at</tt> (cron jobs)\n"
    "- <tt>/usr/local</tt> (instalacoes fora do OSTree)\n\n"
    "<i>Excluindo</i> <tt>/usr</tt>, <tt>/boot</tt>, <tt>/ostree</tt>, "
    "<tt>/sysroot</tt> — gerenciados pelo OSTree."
)


class AboutTab(Adw.Bin):
    def __init__(self) -> None:
        super().__init__()
        self._path_rows: list = []
        self._profile_rows: list = []
        self._running = False

        # ---- About card ---- #
        about_group = Adw.PreferencesGroup()
        about_group.set_title("Como funciona")
        about_group.add(self._wrap_markup_in_row(ABOUT_TEXT))

        # ---- Profile group ---- #
        self._profile_group = Adw.PreferencesGroup()
        self._profile_group.set_title("Perfil ativo")
        self._profile_group.set_description(
            "Qual `aide.conf` esta sendo usado pelas operacoes."
        )

        # ---- System info ---- #
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

        # ---- Watched paths ---- #
        self._paths_group = Adw.PreferencesGroup()
        self._paths_group.set_title("Caminhos monitorados")
        self._paths_group.set_description(
            "Extraido do config do perfil ativo. Para customizar, edite o "
            "arquivo (precisa root)."
        )

        # ---- Layout ---- #
        page = Adw.PreferencesPage()
        page.add(about_group)
        page.add(self._profile_group)
        page.add(sys_group)
        page.add(self._paths_group)
        self.set_child(page)

        self.refresh()

    # ============================================================
    # Helpers
    # ============================================================

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

    # ============================================================
    # Refresh
    # ============================================================

    def refresh(self) -> None:
        active_profile = backend.active_profile_name()
        is_silverblue = backend.silverblue_profile_active()
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

        # Profile group — rebuild rows
        for r in self._profile_rows:
            self._profile_group.remove(r)
        self._profile_rows = []

        status_row = Adw.ActionRow(title="Em uso")
        status_row.add_css_class("property")
        badge = Gtk.Label(label=active_profile)
        badge.add_css_class("monospace")
        badge.add_css_class("success" if is_silverblue else "dim-label")
        status_row.add_suffix(badge)
        self._profile_group.add(status_row)
        self._profile_rows.append(status_row)

        # Texto explicativo + acao
        info_row = self._wrap_markup_in_row(SILVERBLUE_PROFILE_TEXT)
        self._profile_group.add(info_row)
        self._profile_rows.append(info_row)

        action_row = Adw.ActionRow()
        self._profile_btn = Gtk.Button()
        self._profile_btn.set_valign(Gtk.Align.CENTER)
        self._profile_btn.add_css_class("pill")
        action_row.add_suffix(self._profile_btn)

        if is_silverblue:
            action_row.set_title("Voltar ao perfil padrao do sistema")
            action_row.set_subtitle(
                "Remove /etc/aide-vigia.conf e o db Vigia. AIDE volta a usar "
                "/etc/aide.conf padrao."
            )
            self._profile_btn.set_label("Remover")
            self._profile_btn.add_css_class("destructive-action")
            self._profile_btn.connect("clicked", self._on_remove_clicked)
        else:
            action_row.set_title("Aplicar perfil Silverblue")
            action_row.set_subtitle(
                "Instala /etc/aide-vigia.conf otimizado. Vai exigir criar "
                "um novo baseline depois."
            )
            self._profile_btn.set_label("Aplicar")
            self._profile_btn.add_css_class("suggested-action")
            self._profile_btn.connect("clicked", self._on_apply_clicked)

        self._profile_btn.set_sensitive(not self._running and installed)
        self._profile_group.add(action_row)
        self._profile_rows.append(action_row)

        # Paths
        for r in self._path_rows:
            self._paths_group.remove(r)
        self._path_rows = []

        paths = backend.parse_conf_watched_paths()
        if not paths:
            row = Adw.ActionRow(title="Nenhum path detectado")
            row.set_subtitle(
                f"Verifique se {conf_path} existe e tem entradas validas."
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

    # ============================================================
    # Profile actions
    # ============================================================

    def _on_apply_clicked(self, _btn: Gtk.Button) -> None:
        dlg = Adw.AlertDialog(
            heading="Aplicar perfil Silverblue?",
            body=(
                "Vai criar /etc/aide-vigia.conf otimizado para sistemas "
                "atomicos.\n\nSe ja existir um baseline do perfil padrao, "
                "ele NAO sera deletado — fica disponivel se voce voltar "
                "ao perfil padrao depois.\n\nApos aplicar, voce vai "
                "precisar criar um baseline novo na aba Status."
            ),
        )
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("apply", "Aplicar")
        dlg.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("cancel")
        dlg.connect("response", self._on_apply_confirmed)
        dlg.present(self.get_root())

    def _on_apply_confirmed(self, _dlg, response: str) -> None:
        if response != "apply":
            return
        self._running = True
        self._profile_btn.set_sensitive(False)
        threading.Thread(target=self._apply_worker, daemon=True).start()

    def _apply_worker(self) -> None:
        try:
            ok, err = backend.apply_silverblue_profile()
        except Exception as e:  # pylint: disable=broad-except
            ok, err = False, f"Excecao: {e}"
        GLib.idle_add(self._on_apply_done, ok, err)

    def _on_apply_done(self, ok: bool, err: str) -> bool:
        self._running = False
        if not ok:
            show_error(self, "Falha ao aplicar perfil", err)
        else:
            show_info(
                self,
                "Perfil Silverblue aplicado",
                "Va para a aba Status e clique 'Criar baseline' para "
                "comecar a monitorar com o novo perfil.",
            )
        self.refresh()
        return False

    def _on_remove_clicked(self, _btn: Gtk.Button) -> None:
        dlg = Adw.AlertDialog(
            heading="Voltar ao perfil padrao?",
            body=(
                "Vai deletar:\n"
                "- /etc/aide-vigia.conf\n"
                "- /var/lib/aide/aide.db.vigia.gz (baseline)\n\n"
                "AIDE volta a usar /etc/aide.conf padrao (que monitora "
                "/usr, /boot, etc. — gera ruido em Silverblue).\n\n"
                "O baseline do perfil padrao (/var/lib/aide/aide.db.gz), "
                "se houver, NAO sera tocado."
            ),
        )
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("remove", "Remover")
        dlg.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("cancel")
        dlg.connect("response", self._on_remove_confirmed)
        dlg.present(self.get_root())

    def _on_remove_confirmed(self, _dlg, response: str) -> None:
        if response != "remove":
            return
        self._running = True
        self._profile_btn.set_sensitive(False)
        threading.Thread(target=self._remove_worker, daemon=True).start()

    def _remove_worker(self) -> None:
        try:
            ok, err = backend.remove_silverblue_profile()
        except Exception as e:  # pylint: disable=broad-except
            ok, err = False, f"Excecao: {e}"
        GLib.idle_add(self._on_remove_done, ok, err)

    def _on_remove_done(self, ok: bool, err: str) -> bool:
        self._running = False
        if not ok:
            show_error(self, "Falha ao remover perfil", err)
        else:
            show_info(
                self,
                "Perfil padrao ativo",
                "AIDE voltou a usar /etc/aide.conf. Va para Status para "
                "fazer um baseline com o perfil sistema (se ainda nao tiver).",
            )
        self.refresh()
        return False
