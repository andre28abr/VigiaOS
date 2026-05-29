"""Tab Status (v0.3.0 — dnscrypt-only).

Hero sempre reflete dnscrypt-proxy. Sem switch de modo (removido na v0.3).
Quando dnscrypt nao esta ativo, hero mostra estado + botao 'Ativar'.

Acoes:
- Atualizar (refresh manual)
- Limpar cache DNS (`pkill -SIGUSR1 dnscrypt-proxy` ou similar)
- Ativar dnscrypt-proxy (se inativo) — chama migration.ensure_dnscrypt_active
- Restaurar systemd-resolved padrao (caminho de uninstall)
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


class StatusTab(Adw.Bin):
    """Hero dnscrypt + acoes de setup."""

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        # Callback opcional pra notificar window.py quando o estado de
        # ativacao muda (refresca outras tabs)
        self.on_activation_changed: callable | None = None

        # ===== Hero =====
        self._hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._hero.set_halign(Gtk.Align.CENTER)
        self._hero.set_margin_top(32)
        self._hero.set_margin_bottom(20)

        self._state_label = Gtk.Label(label="Verificando...")
        self._state_label.add_css_class("title-1")
        self._state_label.set_halign(Gtk.Align.CENTER)

        self._state_sub = Gtk.Label(label="")
        self._state_sub.add_css_class("title-4")
        self._state_sub.add_css_class("dim-label")
        self._state_sub.set_halign(Gtk.Align.CENTER)
        self._state_sub.set_wrap(True)
        self._state_sub.set_justify(Gtk.Justification.CENTER)
        self._state_sub.set_max_width_chars(56)

        self._hero.append(self._state_label)
        self._hero.append(self._state_sub)

        # ===== Action bar =====
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_halign(Gtk.Align.CENTER)
        action_box.set_margin_bottom(20)

        self._refresh_btn = Gtk.Button(label="Atualizar")
        self._refresh_btn.connect("clicked", lambda _b: self.refresh())
        action_box.append(self._refresh_btn)

        # "Ativar" so aparece quando dnscrypt nao esta rodando
        self._activate_btn = Gtk.Button(label="Ativar dnscrypt-proxy")
        self._activate_btn.add_css_class("suggested-action")
        self._activate_btn.connect("clicked", self._on_activate_clicked)
        self._activate_btn.set_visible(False)
        action_box.append(self._activate_btn)

        self._restore_btn = Gtk.Button(label="Restaurar systemd-resolved")
        self._restore_btn.add_css_class("destructive-action")
        self._restore_btn.set_tooltip_text(
            "Desativa dnscrypt-proxy e restaura systemd-resolved padrão. "
            "Pra quem quer parar de usar o DNS Manager."
        )
        self._restore_btn.connect("clicked", self._on_restore_clicked)
        action_box.append(self._restore_btn)

        # ===== Info group =====
        self._info_group = Adw.PreferencesGroup()
        self._info_group.set_title("dnscrypt-proxy")

        self._row_service = Adw.ActionRow(title="Servico")
        self._row_service.add_css_class("property")
        self._lbl_service = Gtk.Label(label="—")
        self._lbl_service.add_css_class("monospace")
        self._row_service.add_suffix(self._lbl_service)
        self._info_group.add(self._row_service)

        self._row_version = Adw.ActionRow(title="Versão")
        self._row_version.add_css_class("property")
        self._lbl_version = Gtk.Label(label="—")
        self._lbl_version.add_css_class("monospace")
        self._row_version.add_suffix(self._lbl_version)
        self._info_group.add(self._row_version)

        self._row_listen = Adw.ActionRow(title="Endereco")
        self._row_listen.add_css_class("property")
        self._lbl_listen = Gtk.Label(label="—")
        self._lbl_listen.add_css_class("monospace")
        self._row_listen.add_suffix(self._lbl_listen)
        self._info_group.add(self._row_listen)

        # ===== Config group =====
        self._cfg_group = Adw.PreferencesGroup()
        self._cfg_group.set_margin_top(24)
        self._cfg_group.set_title("Configuração")

        self._row_servers = Adw.ActionRow(title="Servers ativos")
        self._row_servers.add_css_class("property")
        self._lbl_servers = Gtk.Label(label="—")
        self._lbl_servers.add_css_class("monospace")
        self._lbl_servers.set_selectable(True)
        self._row_servers.add_suffix(self._lbl_servers)
        self._cfg_group.add(self._row_servers)

        self._row_dnssec = Adw.ActionRow(title="Require DNSSEC")
        self._row_dnssec.add_css_class("property")
        self._lbl_dnssec = Gtk.Label(label="—")
        self._lbl_dnssec.add_css_class("monospace")
        self._row_dnssec.add_suffix(self._lbl_dnssec)
        self._cfg_group.add(self._row_dnssec)

        self._row_nolog = Adw.ActionRow(title="Require no-logs")
        self._row_nolog.add_css_class("property")
        self._lbl_nolog = Gtk.Label(label="—")
        self._lbl_nolog.add_css_class("monospace")
        self._row_nolog.add_suffix(self._lbl_nolog)
        self._cfg_group.add(self._row_nolog)

        # ===== Layout =====
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        outer.set_margin_top(0)
        outer.set_margin_bottom(32)
        outer.set_margin_start(28)
        outer.set_margin_end(28)
        outer.append(self._hero)
        outer.append(action_box)
        outer.append(self._info_group)
        outer.append(self._cfg_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

        self.refresh()

    # ============================================================
    # Refresh
    # ============================================================

    def refresh(self) -> None:
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        try:
            installed = dc.dnscrypt_installed()
            st = dc.get_status() if installed else dc.DnsCryptStatus()
            ready = migration.dnscrypt_active_ready() if installed else False
        except Exception as e:  # pylint: disable=broad-except
            print(f"[status] refresh worker falhou: {e}", flush=True)
            installed, st, ready = False, dc.DnsCryptStatus(), False
        GLib.idle_add(self._apply, installed, st, ready)

    def _apply(self, installed: bool, st, ready: bool) -> bool:
        # Hero
        for cls in ("success", "warning", "error", "dim-label"):
            self._state_label.remove_css_class(cls)

        if not installed:
            self._state_label.set_label("dnscrypt-proxy não instalado")
            self._state_label.add_css_class("error")
            self._state_sub.set_label(
                "Instale via Vigia Tool Installer (rpm-ostree install dnscrypt-proxy)."
            )
            self._activate_btn.set_visible(False)
            self._restore_btn.set_sensitive(False)
        elif not st.active:
            self._state_label.set_label("dnscrypt-proxy parado")
            self._state_label.add_css_class("warning")
            self._state_sub.set_label(
                "Instalado mas não rodando. Clique em 'Ativar dnscrypt-proxy' "
                "para configurar como backend DNS do sistema."
            )
            self._activate_btn.set_visible(True)
            self._restore_btn.set_sensitive(True)
        elif not ready:
            self._state_label.set_label("Quase lá")
            self._state_label.add_css_class("warning")
            self._state_sub.set_label(
                "dnscrypt-proxy está rodando, mas o sistema não está apontando "
                "pra ele. Clique 'Ativar' pra ajustar /etc/resolv.conf."
            )
            self._activate_btn.set_visible(True)
            self._restore_btn.set_sensitive(True)
        else:
            self._state_label.set_label("Ativo e seguro")
            self._state_label.add_css_class("success")
            features = []
            if st.server_names:
                features.append(f"{len(st.server_names)} server(s)")
            if st.require_dnssec:
                features.append("DNSSEC")
            if st.require_nolog:
                features.append("no-logs")
            sub = "dnscrypt-proxy · " + " · ".join(features) if features else \
                  "dnscrypt-proxy rodando"
            self._state_sub.set_label(sub)
            self._activate_btn.set_visible(False)
            self._restore_btn.set_sensitive(True)

        # Info group
        for cls in ("success", "warning", "error", "dim-label"):
            self._lbl_service.remove_css_class(cls)
        if not installed:
            self._lbl_service.set_label("não instalado")
            self._lbl_service.add_css_class("error")
        elif st.active:
            self._lbl_service.set_label("ativo" + (" (enabled)" if st.enabled else " (não enabled)"))
            self._lbl_service.add_css_class("success")
        else:
            self._lbl_service.set_label("parado")
            self._lbl_service.add_css_class("warning")

        for cls in ("dim-label",):
            self._lbl_version.remove_css_class(cls)
        if st.version:
            self._lbl_version.set_label(st.version)
        else:
            self._lbl_version.set_label("—")
            self._lbl_version.add_css_class("dim-label")

        self._lbl_listen.set_label(st.listen_address or "127.0.0.1:53")

        # Config group
        if st.server_names:
            self._lbl_servers.set_label(", ".join(st.server_names))
        else:
            self._lbl_servers.set_label("(nenhum — use a aba Provedores)")
            self._lbl_servers.add_css_class("dim-label")

        for cls in ("success", "warning"):
            self._lbl_dnssec.remove_css_class(cls)
        if st.require_dnssec:
            self._lbl_dnssec.set_label("sim")
            self._lbl_dnssec.add_css_class("success")
        else:
            self._lbl_dnssec.set_label("não")
            self._lbl_dnssec.add_css_class("warning")

        for cls in ("success", "warning"):
            self._lbl_nolog.remove_css_class(cls)
        if st.require_nolog:
            self._lbl_nolog.set_label("sim")
            self._lbl_nolog.add_css_class("success")
        else:
            self._lbl_nolog.set_label("não")
            self._lbl_nolog.add_css_class("warning")

        return False

    # ============================================================
    # Ativar dnscrypt-proxy (primeira execucao ou apos restore)
    # ============================================================

    def _on_activate_clicked(self, _btn: Gtk.Button) -> None:
        if self._running:
            return
        dlg = Adw.AlertDialog(
            heading="Ativar dnscrypt-proxy como backend DNS?",
            body=(
                "Esta ação:\n"
                "• Faz backup de /etc/systemd/resolved.conf e /etc/resolv.conf\n"
                "• Para o systemd-resolved (libera porta 53)\n"
                "• Inicia o dnscrypt-proxy em 127.0.0.1\n"
                "• Aponta /etc/resolv.conf para 127.0.0.1\n\n"
                "Você pode reverter a qualquer momento via 'Restaurar systemd-resolved'.\n\n"
                "Será pedida senha admin (pkexec)."
            ),
        )
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("activate", "Ativar")
        dlg.set_response_appearance("activate", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("cancel")
        dlg.connect("response", self._on_activate_response)
        dlg.present(self.get_root())

    def _on_activate_response(self, _dlg, response: str) -> None:
        if response != "activate":
            return
        self._running = True
        self._activate_btn.set_sensitive(False)
        threading.Thread(target=self._activate_worker, daemon=True).start()

    def _activate_worker(self) -> None:
        try:
            ok, err = migration.ensure_dnscrypt_active_blocking()
        except Exception as e:  # pylint: disable=broad-except
            ok, err = False, f"Excecao: {e}"
        GLib.idle_add(self._on_activate_done, ok, err)

    def _on_activate_done(self, ok: bool, err: str) -> bool:
        self._running = False
        self._activate_btn.set_sensitive(True)
        if not ok:
            show_error(self, "Falha ao ativar dnscrypt-proxy", err)
        else:
            show_info(
                self, "dnscrypt-proxy ativo",
                "Backend DNS do sistema agora é dnscrypt-proxy. "
                "Pode levar alguns segundos para todas as queries começarem "
                "a passar pelo novo resolver.",
            )
            self.refresh()
            if self.on_activation_changed is not None:
                try:
                    self.on_activation_changed()
                except Exception:  # pylint: disable=broad-except
                    pass
        return False

    # ============================================================
    # Restore systemd-resolved (uninstall path)
    # ============================================================

    def _on_restore_clicked(self, _btn: Gtk.Button) -> None:
        dlg = Adw.AlertDialog(
            heading="Restaurar systemd-resolved padrão?",
            body=(
                "Esta ação DESATIVA o dnscrypt-proxy e volta o sistema ao "
                "default Fedora (systemd-resolved). Recomendado se você "
                "quer parar de usar o DNS Manager.\n\n"
                "O que acontece:\n"
                "• Para e desabilita dnscrypt-proxy\n"
                "• Restaura /etc/systemd/resolved.conf do backup\n"
                "• Restaura /etc/resolv.conf -> stub-resolv.conf\n"
                "• Inicia systemd-resolved\n\n"
                "O pacote dnscrypt-proxy NÃO é desinstalado — você pode "
                "reativar a qualquer momento. Será pedida senha admin."
            ),
        )
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("restore", "Restaurar")
        dlg.set_response_appearance("restore", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("cancel")
        dlg.connect("response", self._on_restore_response)
        dlg.present(self.get_root())

    def _on_restore_response(self, _dlg, response: str) -> None:
        if response != "restore":
            return
        self._running = True
        self._restore_btn.set_sensitive(False)
        threading.Thread(target=self._restore_worker, daemon=True).start()

    def _restore_worker(self) -> None:
        try:
            ok, err = migration.restore_systemd_resolved_blocking()
        except Exception as e:  # pylint: disable=broad-except
            ok, err = False, f"Excecao: {e}"
        GLib.idle_add(self._on_restore_done, ok, err)

    def _on_restore_done(self, ok: bool, err: str) -> bool:
        self._running = False
        self._restore_btn.set_sensitive(True)
        if not ok:
            show_error(self, "Falha ao restaurar", err)
        else:
            show_info(
                self, "systemd-resolved restaurado",
                "DNS do sistema voltou ao default Fedora. O dnscrypt-proxy "
                "está parado mas continua instalado. Pode reativar a qualquer "
                "momento via 'Ativar dnscrypt-proxy'.",
            )
            self.refresh()
            if self.on_activation_changed is not None:
                try:
                    self.on_activation_changed()
                except Exception:  # pylint: disable=broad-except
                    pass
        return False
