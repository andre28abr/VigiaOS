"""Tab Status: estado atual dos resolvers DNS."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from .. import dnscrypt_backend as dc
from .. import migration
from .._resolvers_module import find_resolver_for_servers
from ._helpers import make_clamp, show_error, show_info


class StatusTab(Adw.Bin):
    """Hero + interfaces + acoes (flush, restore)."""

    def __init__(self) -> None:
        super().__init__()
        self._iface_rows: list = []
        self._running = False
        # Callback chamado quando modo avancado e' ativado/desativado.
        # Window.py seta isso para refrescar Blocklists/Stats que
        # dependem do mode atual.
        self.on_mode_changed: callable | None = None

        # v0.2.8: cache do ultimo estado conhecido + hint. Resolve o
        # caso: user clica Aplicar em Provedores, vai pra Status, hero
        # demora ~2min pra ficar verde pq resolvectl status retorna
        # Global vazio em race. Com cache/hint, hero atualiza imediato.
        self._last_known_dns: list[str] = []   # cache do current/global
        self._last_known_dot: str = ""

        # Hero
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

        # Action bar
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_halign(Gtk.Align.CENTER)
        action_box.set_margin_bottom(20)

        self._refresh_btn = Gtk.Button(label="Atualizar")
        self._refresh_btn.connect("clicked", lambda _b: self.refresh())
        action_box.append(self._refresh_btn)

        self._flush_btn = Gtk.Button(label="Limpar cache DNS")
        self._flush_btn.connect("clicked", self._on_flush_clicked)
        action_box.append(self._flush_btn)

        self._restore_btn = Gtk.Button(label="Restaurar padrao")
        self._restore_btn.add_css_class("destructive-action")
        self._restore_btn.set_tooltip_text(
            "Restaura /etc/systemd/resolved.conf do backup (se houver)"
        )
        self._restore_btn.connect("clicked", self._on_restore_clicked)
        action_box.append(self._restore_btn)

        # Global config group
        self._global_group = Adw.PreferencesGroup()
        self._global_group.set_title("Configuracao global")

        self._row_dns = Adw.ActionRow(title="DNS configurado")
        self._row_dns.add_css_class("property")
        self._lbl_dns = Gtk.Label(label="—")
        self._lbl_dns.add_css_class("monospace")
        self._lbl_dns.set_selectable(True)
        self._row_dns.add_suffix(self._lbl_dns)
        self._global_group.add(self._row_dns)

        self._row_provider = Adw.ActionRow(title="Provedor identificado")
        self._row_provider.add_css_class("property")
        self._lbl_provider = Gtk.Label(label="—")
        self._lbl_provider.add_css_class("monospace")
        self._row_provider.add_suffix(self._lbl_provider)
        self._global_group.add(self._row_provider)

        self._row_dot = Adw.ActionRow(title="DNS over TLS (DoT)")
        self._row_dot.add_css_class("property")
        self._row_dot.set_subtitle("Encripta as queries entre voce e o resolver")
        self._lbl_dot = Gtk.Label(label="—")
        self._lbl_dot.add_css_class("monospace")
        self._row_dot.add_suffix(self._lbl_dot)
        self._global_group.add(self._row_dot)

        # Interfaces group
        self._ifaces_group = Adw.PreferencesGroup()
        self._ifaces_group.set_margin_top(24)
        self._ifaces_group.set_title("Interfaces de rede")
        self._ifaces_group.set_description(
            "DNS configurado por interface (NetworkManager/dhcpcd) — sobrescreve o global."
        )

        # System info
        self._sys_group = Adw.PreferencesGroup()
        self._sys_group.set_margin_top(24)
        self._sys_group.set_title("Sistema")
        self._row_resolved = Adw.ActionRow(title="systemd-resolved")
        self._row_resolved.add_css_class("property")
        self._lbl_resolved = Gtk.Label(label="—")
        self._lbl_resolved.add_css_class("monospace")
        self._row_resolved.add_suffix(self._lbl_resolved)
        self._sys_group.add(self._row_resolved)

        # ===== Modo avancado (v0.2): switch + info dnscrypt-proxy =====
        self._adv_group = Adw.PreferencesGroup()
        self._adv_group.set_margin_top(24)
        self._adv_group.set_title("Modo avancado (v0.2)")
        self._adv_group.set_description(
            "Substitui systemd-resolved por dnscrypt-proxy. Habilita "
            "DoH, blocklists locais, anonymized DNS e estatisticas. "
            "Requer dnscrypt-proxy instalado."
        )

        # Switch row para alternar modo
        self._adv_switch_row = Adw.SwitchRow()
        self._adv_switch_row.set_title("Ativar modo avancado")
        self._adv_switch_row.set_subtitle(
            "Faz backup de resolved.conf e ativa dnscrypt-proxy em 127.0.0.1"
        )
        # Connect via handler_id para suprimir signal quando atualizamos
        # programaticamente o estado do switch
        self._adv_switch_handler = self._adv_switch_row.connect(
            "notify::active", self._on_adv_switch_toggled
        )
        self._adv_group.add(self._adv_switch_row)

        # Info dnscrypt-proxy
        self._adv_status_row = Adw.ActionRow(title="dnscrypt-proxy")
        self._adv_status_row.add_css_class("property")
        self._lbl_adv_status = Gtk.Label(label="—")
        self._lbl_adv_status.add_css_class("monospace")
        self._adv_status_row.add_suffix(self._lbl_adv_status)
        self._adv_group.add(self._adv_status_row)

        self._adv_version_row = Adw.ActionRow(title="Versao")
        self._adv_version_row.add_css_class("property")
        self._lbl_adv_version = Gtk.Label(label="—")
        self._lbl_adv_version.add_css_class("monospace")
        self._adv_version_row.add_suffix(self._lbl_adv_version)
        self._adv_group.add(self._adv_version_row)

        # Layout
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        outer.set_margin_top(0)
        outer.set_margin_bottom(32)
        outer.set_margin_start(28)
        outer.set_margin_end(28)
        outer.append(self._hero)
        outer.append(action_box)
        outer.append(self._global_group)
        outer.append(self._ifaces_group)
        outer.append(self._sys_group)
        outer.append(self._adv_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

        self.refresh()

    # ============================================================
    # API publica
    # ============================================================

    def invalidate_cache(self) -> None:
        """Zera o cache do status (v0.2.8).

        Window.py chama em mode switch — apos a migration, o cache de
        DNS anterior nao se aplica mais.
        """
        self._last_known_dns = []
        self._last_known_dot = ""

    # ============================================================
    # Refresh (async — resolvectl pode ser lento em sistemas estresados)
    # ============================================================

    def refresh(self, expected_dns: list[str] | None = None,
                expected_dot: str | None = None) -> None:
        """Recarrega status.

        v0.2.8: aceita hint `expected_dns` (lista IPs) e `expected_dot`
        ('yes'/'no'). Caller (window.py) passa apos um Apply bem-sucedido
        em Provedores, pra que o hero ja fique verde imediatamente
        sem esperar o sistema reportar.
        """
        threading.Thread(
            target=self._refresh_worker,
            args=(expected_dns or [], expected_dot or ""),
            daemon=True,
        ).start()

    def _refresh_worker(self, expected_dns: list[str], expected_dot: str) -> None:
        try:
            st = backend.get_status()
        except Exception as e:  # pylint: disable=broad-except
            print(f"[status] backend.get_status falhou: {e}", flush=True)
            st = backend.ResolvedStatus()
        # v0.2: tambem coleta status do dnscrypt-proxy
        try:
            dc_st = dc.get_status()
        except Exception as e:  # pylint: disable=broad-except
            print(f"[status] dc.get_status falhou: {e}", flush=True)
            dc_st = dc.DnsCryptStatus()
        try:
            mode = migration.get_current_mode()
        except Exception as e:  # pylint: disable=broad-except
            print(f"[status] get_current_mode falhou: {e}", flush=True)
            mode = "unknown"

        # v0.2.8: optimistic merge — se o sistema retornou DNS vazio mas
        # temos hint OU cache, usa eles. Assim hero fica verde imediato
        # mesmo enquanto resolvectl status ainda nao propagou.
        if not st.current_dns and not st.global_dns:
            if expected_dns:
                st.global_dns = list(expected_dns)
            elif self._last_known_dns:
                st.global_dns = list(self._last_known_dns)
        if not st.global_dot and expected_dot:
            st.global_dot = expected_dot
        elif not st.global_dot and self._last_known_dot:
            st.global_dot = self._last_known_dot

        GLib.idle_add(self._apply, st, dc_st, mode)

    def _apply(self, st: backend.ResolvedStatus, dc_st=None, mode: str = "unknown") -> bool:
        # v0.2.8: atualiza cache com dados nao-vazios (se vier vazio,
        # preserva o que tinha — _refresh_worker ja faz fallback)
        if st.current_dns or st.global_dns:
            self._last_known_dns = list(st.current_dns or st.global_dns)
        if st.global_dot:
            self._last_known_dot = st.global_dot

        # Hero (v0.2.2: mode-aware)
        for cls in ("success", "warning", "error", "dim-label"):
            self._state_label.remove_css_class(cls)

        # Se modo avancado esta ativo, hero reflete dnscrypt-proxy
        # (nao reclama de systemd-resolved estar parado — esse e' o design!)
        if mode == "advanced" and dc_st is not None and dc_st.active:
            self._state_label.set_label("Modo avancado ativo")
            self._state_label.add_css_class("success")
            features = []
            if dc_st.server_names:
                features.append(f"{len(dc_st.server_names)} server(s)")
            if dc_st.blocklist_size > 0:
                features.append(f"{dc_st.blocklist_size} dominios bloqueados")
            else:
                features.append("blocklist vazia")
            if dc_st.require_dnssec:
                features.append("DNSSEC")
            sub = "dnscrypt-proxy em 127.0.0.1 · " + " · ".join(features)
            self._state_sub.set_label(sub)
        elif not st.available:
            self._state_label.set_label("systemd-resolved nao disponivel")
            self._state_label.add_css_class("error")
            self._state_sub.set_label(
                "Comando 'resolvectl' nao encontrado. Em Silverblue ja vem por padrao."
            )
        elif not st.active:
            self._state_label.set_label("systemd-resolved parado")
            self._state_label.add_css_class("warning")
            self._state_sub.set_label(
                "Service nao esta running. Tente: sudo systemctl start systemd-resolved"
            )
        elif not st.current_dns and not st.global_dns:
            self._state_label.set_label("Sem DNS configurado")
            self._state_label.add_css_class("warning")
            self._state_sub.set_label(
                "Nenhum resolver detectado. Use a aba 'Resolvers' para escolher um."
            )
        else:
            provider = find_resolver_for_servers(
                st.current_dns or st.global_dns
            )
            if provider:
                self._state_label.set_label(provider.name)
                self._state_label.add_css_class("success")
                self._state_sub.set_label(provider.description)
            else:
                self._state_label.set_label("DNS configurado")
                self._state_label.add_css_class("success")
                primary = (st.current_dns or st.global_dns)[0]
                self._state_sub.set_label(f"Usando: {primary}")

        # Sistema — quando modo avancado ativo, systemd-resolved parado e'
        # esperado (nao e' warning). Mostra como dim-label.
        for cls in ("success", "error", "warning", "dim-label"):
            self._lbl_resolved.remove_css_class(cls)
        if st.active:
            self._lbl_resolved.set_label("ativo")
            self._lbl_resolved.add_css_class("success")
        elif st.available:
            if mode == "advanced":
                # Esperado em modo avancado — dnscrypt-proxy substitui ele
                self._lbl_resolved.set_label("parado (modo avancado)")
                self._lbl_resolved.add_css_class("dim-label")
            else:
                self._lbl_resolved.set_label("parado")
                self._lbl_resolved.add_css_class("warning")
        else:
            self._lbl_resolved.set_label("indisponivel")
            self._lbl_resolved.add_css_class("error")

        # v0.2.2: esconde grupos relativos a systemd-resolved quando
        # modo avancado esta ativo. Esses grupos so fazem sentido quando
        # o backend e' systemd-resolved.
        is_advanced = (mode == "advanced")
        self._global_group.set_visible(not is_advanced)
        self._ifaces_group.set_visible(not is_advanced)

        # Global config
        if st.global_dns:
            self._lbl_dns.set_label(", ".join(st.global_dns))
        else:
            self._lbl_dns.set_label("(nenhum no [Resolve] config)")
            self._lbl_dns.add_css_class("dim-label")

        provider = find_resolver_for_servers(st.current_dns or st.global_dns)
        if provider:
            self._lbl_provider.set_label(provider.name)
            self._lbl_provider.remove_css_class("dim-label")
        else:
            self._lbl_provider.set_label("(desconhecido)")
            self._lbl_provider.add_css_class("dim-label")

        for cls in ("success", "warning", "dim-label"):
            self._lbl_dot.remove_css_class(cls)
        if st.global_dot == "yes":
            self._lbl_dot.set_label("habilitado")
            self._lbl_dot.add_css_class("success")
        elif st.global_dot == "no":
            self._lbl_dot.set_label("desabilitado")
            self._lbl_dot.add_css_class("warning")
        else:
            self._lbl_dot.set_label("(default)")
            self._lbl_dot.add_css_class("dim-label")

        # Interfaces
        for r in self._iface_rows:
            self._ifaces_group.remove(r)
        self._iface_rows = []

        if not st.interfaces:
            row = Adw.ActionRow(title="Nenhuma interface")
            row.set_subtitle(
                "DNS so do [Global]. Em redes domesticas, o NetworkManager "
                "tipicamente fornece DNS por interface — verifique o roteador."
            )
            row.add_css_class("dim-label")
            self._ifaces_group.add(row)
            self._iface_rows.append(row)
        else:
            for iface in st.interfaces:
                row = Adw.ExpanderRow()
                row.set_title(iface.name)
                if iface.dns_servers:
                    row.set_subtitle(", ".join(iface.dns_servers))
                else:
                    row.set_subtitle("(sem DNS na interface)")

                if iface.dns_over_tls:
                    dot_row = Adw.ActionRow(title="DNS over TLS")
                    dot_row.add_css_class("property")
                    dot_lbl = Gtk.Label(label=iface.dns_over_tls)
                    dot_lbl.add_css_class("monospace")
                    if iface.dns_over_tls == "yes":
                        dot_lbl.add_css_class("success")
                    else:
                        dot_lbl.add_css_class("dim-label")
                    dot_row.add_suffix(dot_lbl)
                    row.add_row(dot_row)

                if iface.domains:
                    dom_row = Adw.ActionRow(title="Search domains")
                    dom_row.add_css_class("property")
                    dom_lbl = Gtk.Label(label=", ".join(iface.domains))
                    dom_lbl.add_css_class("monospace")
                    dom_row.add_suffix(dom_lbl)
                    row.add_row(dom_row)

                self._ifaces_group.add(row)
                self._iface_rows.append(row)

        # ===== v0.2: dnscrypt-proxy info + switch state =====
        if dc_st is not None:
            self._update_advanced_section(dc_st, mode)

        return False

    def _update_advanced_section(self, dc_st, mode: str) -> None:
        """Atualiza secao 'Modo avancado' com info do dnscrypt-proxy."""
        # Suprime signal do switch enquanto setamos programaticamente
        self._adv_switch_row.handler_block(self._adv_switch_handler)
        try:
            advanced_active = (mode == "advanced")
            self._adv_switch_row.set_active(advanced_active)
            # Desabilita switch se dnscrypt-proxy nao esta instalado
            self._adv_switch_row.set_sensitive(dc_st.installed)
            if not dc_st.installed:
                self._adv_switch_row.set_subtitle(
                    "dnscrypt-proxy nao instalado — instale via Vigia Tool Installer"
                )
            elif advanced_active:
                self._adv_switch_row.set_subtitle(
                    f"Ativo · {len(dc_st.server_names)} servers configurados"
                )
            else:
                self._adv_switch_row.set_subtitle(
                    "Faz backup de resolved.conf e ativa dnscrypt-proxy em 127.0.0.1"
                )
        finally:
            self._adv_switch_row.handler_unblock(self._adv_switch_handler)

        # dnscrypt-proxy status label
        for cls in ("success", "warning", "error", "dim-label"):
            self._lbl_adv_status.remove_css_class(cls)
        if not dc_st.installed:
            self._lbl_adv_status.set_label("nao instalado")
            self._lbl_adv_status.add_css_class("dim-label")
        elif dc_st.active:
            self._lbl_adv_status.set_label("ativo")
            self._lbl_adv_status.add_css_class("success")
        else:
            self._lbl_adv_status.set_label("inativo")
            self._lbl_adv_status.add_css_class("warning")

        # Versao
        for cls in ("dim-label",):
            self._lbl_adv_version.remove_css_class(cls)
        if dc_st.version:
            self._lbl_adv_version.set_label(dc_st.version)
        else:
            self._lbl_adv_version.set_label("—")
            self._lbl_adv_version.add_css_class("dim-label")

    # ============================================================
    # v0.2: Switch de modo avancado
    # ============================================================

    def _on_adv_switch_toggled(self, switch_row: Adw.SwitchRow, _pspec) -> None:
        """Handler do switch: confirma e dispara migration."""
        if self._running:
            return
        new_state = switch_row.get_active()

        # Confirma com dialog
        if new_state:
            heading = "Ativar modo avancado (dnscrypt-proxy)?"
            body = (
                "Esta acao:\n"
                "• Faz backup de /etc/systemd/resolved.conf\n"
                "• Desativa o systemd-resolved\n"
                "• Ativa o dnscrypt-proxy em 127.0.0.1\n"
                "• Aponta /etc/resolv.conf para 127.0.0.1\n\n"
                "Voce pode reverter a qualquer momento desligando este switch. "
                "Sera pedida senha admin (pkexec)."
            )
            response_label = "Ativar"
            response_appearance = Adw.ResponseAppearance.SUGGESTED
        else:
            heading = "Desativar modo avancado?"
            body = (
                "Esta acao:\n"
                "• Desativa o dnscrypt-proxy\n"
                "• Restaura /etc/systemd/resolved.conf do backup\n"
                "• Restaura /etc/resolv.conf\n"
                "• Reativa o systemd-resolved\n\n"
                "Sera pedida senha admin (pkexec)."
            )
            response_label = "Desativar"
            response_appearance = Adw.ResponseAppearance.DESTRUCTIVE

        dlg = Adw.AlertDialog(heading=heading, body=body)
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("confirm", response_label)
        dlg.set_default_response("cancel")
        dlg.set_response_appearance("confirm", response_appearance)
        dlg.connect("response", self._on_adv_switch_response, new_state)
        dlg.present(self.get_root())

    def _on_adv_switch_response(self, _dlg, response: str, target_state: bool) -> None:
        if response != "confirm":
            # User cancelou — reverte o switch sem disparar signal de novo
            self._adv_switch_row.handler_block(self._adv_switch_handler)
            try:
                self._adv_switch_row.set_active(not target_state)
            finally:
                self._adv_switch_row.handler_unblock(self._adv_switch_handler)
            return

        # Dispara migration em thread
        self._running = True
        self._adv_switch_row.set_sensitive(False)
        threading.Thread(
            target=self._adv_switch_worker, args=(target_state,), daemon=True,
        ).start()

    def _adv_switch_worker(self, target_state: bool) -> None:
        if target_state:
            ok, err = migration.activate_advanced_mode_blocking()
        else:
            ok, err = migration.deactivate_advanced_mode_blocking()
        GLib.idle_add(self._on_adv_switch_done, ok, err, target_state)

    def _on_adv_switch_done(self, ok: bool, err: str, target_state: bool) -> bool:
        self._running = False
        self._adv_switch_row.set_sensitive(True)

        if not ok:
            # Reverte o switch (operacao falhou)
            self._adv_switch_row.handler_block(self._adv_switch_handler)
            try:
                self._adv_switch_row.set_active(not target_state)
            finally:
                self._adv_switch_row.handler_unblock(self._adv_switch_handler)
            show_error(
                self,
                "Falha ao alterar modo",
                err or "Operacao retornou erro desconhecido.",
            )
        else:
            label = "ativado" if target_state else "desativado"
            show_info(
                self,
                f"Modo avancado {label}",
                "Operacao concluida. Pode levar alguns segundos para todas as "
                "queries comecarem a passar pelo novo resolver.",
            )
            # Refresh imediato para reverificar estado proprio
            self.refresh()
            # Notifica tabs irmaos (Blocklists, Stats) que dependem do modo
            if self.on_mode_changed is not None:
                try:
                    self.on_mode_changed()
                except Exception:  # pylint: disable=broad-except
                    pass
        return False

    # ============================================================
    # Flush cache
    # ============================================================

    def _on_flush_clicked(self, _btn: Gtk.Button) -> None:
        if self._running:
            return
        self._running = True
        self._flush_btn.set_sensitive(False)
        threading.Thread(target=self._flush_worker, daemon=True).start()

    def _flush_worker(self) -> None:
        try:
            ok, err = backend.flush_cache_elevated()
        except Exception as e:  # pylint: disable=broad-except
            ok, err = False, f"Excecao: {e}"
        GLib.idle_add(self._on_flush_done, ok, err)

    def _on_flush_done(self, ok: bool, err: str) -> bool:
        self._running = False
        self._flush_btn.set_sensitive(True)
        if not ok:
            show_error(self, "Falha ao limpar cache", err)
        else:
            show_info(
                self, "Cache limpo",
                "Cache DNS do systemd-resolved foi esvaziado. Proximas "
                "queries vao buscar de novo nos upstream resolvers.",
            )
        return False

    # ============================================================
    # Restore default config
    # ============================================================

    def _on_restore_clicked(self, _btn: Gtk.Button) -> None:
        dlg = Adw.AlertDialog(
            heading="Restaurar /etc/systemd/resolved.conf padrao?",
            body=(
                "Se existir backup criado pelo Vigia "
                "(/etc/systemd/resolved.conf.vigia-backup), restaura ele. "
                "Senao, escreve um config vazio (defaults do systemd-resolved).\n\n"
                "Em ambos os casos, o servico e' reiniciado."
            ),
        )
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("restore", "Restaurar")
        dlg.set_response_appearance("restore", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("cancel")
        dlg.connect("response", self._on_restore_confirmed)
        dlg.present(self.get_root())

    def _on_restore_confirmed(self, _dlg, response: str) -> None:
        if response != "restore":
            return
        self._running = True
        self._restore_btn.set_sensitive(False)
        threading.Thread(target=self._restore_worker, daemon=True).start()

    def _restore_worker(self) -> None:
        try:
            ok, err = backend.restore_default_elevated()
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
                self, "Config restaurado",
                "systemd-resolved reiniciado. DNS volta aos defaults do sistema.",
            )
            self.refresh()
        return False
