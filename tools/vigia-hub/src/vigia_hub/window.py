"""Janela principal do Hub — 3 painéis:

  [nav fina] | [sidebar tools] | [content]
   ~70px       ~280px            flex

A NAV FINA (esquerda) tem 4 modos selecionaveis:
  - 'tools'      — vista padrao master-detail das tools registradas
  - 'installer'  — Tool Installer em fullscreen (movido pra ca em v0.5)
  - 'settings'   — configuracoes globais do Hub (em breve)
  - 'help'       — manuais (em breve)

Em modo 'tools', a SIDEBAR central lista tools agrupadas por
categoria (Monitoramento / Privacidade / Defesa / Relatorios).

O CONTENT (direita) muda conforme:
  - modo != tools           -> ocupa toda area de tools+content
  - modo tools + tool       -> widget embarcado da tool
  - modo tools + indispon.  -> detail page com botao Abrir externamente
"""

from __future__ import annotations

import importlib
import shutil
import subprocess
import traceback

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .markdown import md_to_pango
from .registry import (
    CATEGORY_LABELS,
    TOOLS,
    ToolEntry,
    tools_by_category,
)
from .settings import (
    Settings,
    autostart_is_enabled,
    autostart_sync,
    load_settings,
    save_settings,
)
from .tray.checks import (
    INSTALL_PACKAGES,
    enable_extension_command,
    install_command,
    tray_can_work,
)


# Lista de emuladores de terminal em ordem de preferencia.
TERMINAL_CANDIDATES = [
    ("kgx", ["--"]),
    ("ptyxis", ["--"]),
    ("gnome-terminal", ["--"]),
    ("konsole", ["-e"]),
    ("xterm", ["-e"]),
    ("alacritty", ["-e"]),
]


def find_terminal() -> tuple[str, list[str]] | None:
    for binary, args in TERMINAL_CANDIDATES:
        if shutil.which(binary):
            return binary, args
    return None


# Modos da nav lateral
NAV_MODES = [
    ("tools", "Tools", "view-grid-symbolic"),
    ("installer", "Instalador", "package-x-generic-symbolic"),
    ("settings", "Config.", "preferences-system-symbolic"),
    ("help", "Ajuda", "help-browser-symbolic"),
]


class VigiaHubWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("Vigia Suite")
        self.set_default_size(1340, 820)

        # Cache de widgets embarcados (tools): tool.id -> Gtk.Widget
        self._embedded_widgets: dict[str, Gtk.Widget] = {}
        # Caches de paginas de modo (installer, settings, help)
        self._mode_pages: dict[str, Gtk.Widget] = {}

        # ============= Nav fina (esquerda) ============= #
        nav_box = self._build_nav_bar()

        # ============= Modo Tools (master-detail) ============= #
        self._tools_view = self._build_tools_view()

        # ============= Main stack (alterna entre modos) ============= #
        self._main_stack = Gtk.Stack()
        self._main_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._main_stack.set_transition_duration(150)
        self._main_stack.set_hexpand(True)
        self._main_stack.add_named(self._tools_view, "tools")
        # installer/settings/help: lazy — criados na primeira selecao

        # ============= Layout final ============= #
        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        outer.append(nav_box)
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        outer.append(sep)
        outer.append(self._main_stack)
        self.set_content(outer)

        # Seleciona "tools" por default
        first_row = self._nav_list.get_row_at_index(0)
        if first_row is not None:
            self._nav_list.select_row(first_row)

        # Seleciona primeira tool dentro do modo tools
        if TOOLS:
            first_tool_row = self._sidebar_list.get_row_at_index(0)
            # Pula headers (rows nao-tools)
            while first_tool_row is not None and not getattr(first_tool_row, "_tool_id", None):
                idx = first_tool_row.get_index()
                first_tool_row = self._sidebar_list.get_row_at_index(idx + 1)
            if first_tool_row is not None:
                self._sidebar_list.select_row(first_tool_row)
                tool = self._tool_by_id(getattr(first_tool_row, "_tool_id"))
                if tool is not None:
                    self._show_tool(tool)

    # ========================================================================
    # Nav bar (4 icones)
    # ========================================================================

    def _build_nav_bar(self) -> Gtk.Widget:
        """Barra fina vertical com 4 botoes-icone."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_size_request(74, -1)

        # Header do hub (logo discreto)
        header_lbl = Gtk.Label(label="VIGIA")
        header_lbl.add_css_class("caption-heading")
        header_lbl.add_css_class("dim-label")
        header_lbl.set_margin_top(16)
        header_lbl.set_margin_bottom(20)
        box.append(header_lbl)

        # ListBox dos modos
        self._nav_list = Gtk.ListBox()
        self._nav_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._nav_list.add_css_class("navigation-sidebar")
        self._nav_list.connect("row-selected", self._on_nav_selected)

        for mode_id, label, icon_name in NAV_MODES:
            row = Gtk.ListBoxRow()
            row._mode_id = mode_id  # type: ignore[attr-defined]
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            inner.set_margin_top(10)
            inner.set_margin_bottom(10)
            inner.set_margin_start(6)
            inner.set_margin_end(6)

            icon = Gtk.Image.new_from_icon_name(icon_name)
            icon.set_pixel_size(22)
            icon.set_halign(Gtk.Align.CENTER)
            inner.append(icon)

            lbl = Gtk.Label(label=label)
            lbl.add_css_class("caption")
            lbl.set_halign(Gtk.Align.CENTER)
            inner.append(lbl)

            row.set_child(inner)
            self._nav_list.append(row)

        box.append(self._nav_list)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        box.append(spacer)

        return box

    def _on_nav_selected(
        self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None
    ) -> None:
        if row is None:
            return
        mode_id = getattr(row, "_mode_id", None)
        if not mode_id:
            return

        if mode_id == "tools":
            self._main_stack.set_visible_child_name("tools")
            return

        # Lazy build pages
        if mode_id not in self._mode_pages:
            try:
                page = self._build_mode_page(mode_id)
            except Exception as e:  # pylint: disable=broad-except
                err = "".join(traceback.format_exception_only(type(e), e)).strip()
                page = Adw.StatusPage(
                    title=f"Falha ao carregar '{mode_id}'",
                    description=err,
                    icon_name="dialog-error-symbolic",
                )
            self._mode_pages[mode_id] = page
            self._main_stack.add_named(page, mode_id)

        self._main_stack.set_visible_child_name(mode_id)

    def _build_mode_page(self, mode_id: str) -> Gtk.Widget:
        """Constroi a pagina de um modo (installer/settings/help)."""
        if mode_id == "installer":
            # Importa o Tool Installer e usa build_content() fullscreen
            module = importlib.import_module("vigia_installer.window")
            builder = getattr(module, "build_content", None)
            if not callable(builder):
                raise RuntimeError("vigia_installer.window.build_content() faltando")
            return builder()
        if mode_id == "settings":
            return self._build_settings_page()
        if mode_id == "help":
            inner = Adw.StatusPage(
                title="Manuais",
                description=(
                    "Manuais detalhados de cada tool. Cada tool tambem tem aba "
                    "'Sobre' interna com informacoes especificas. Esta pagina "
                    "consolida tudo num so lugar — em construcao."
                ),
                icon_name="help-browser-symbolic",
            )
            return self._wrap_with_header(inner, "Ajuda")
        raise ValueError(f"Modo desconhecido: {mode_id}")

    def _wrap_with_header(
        self,
        content: Gtk.Widget,
        title: str,
        title_widget: Gtk.Widget | None = None,
    ) -> Gtk.Widget:
        """Envolve content num ToolbarView + HeaderBar (com X de fechar)."""
        header = Adw.HeaderBar()
        if title_widget is not None:
            header.set_title_widget(title_widget)
        else:
            header.set_title_widget(Adw.WindowTitle(title=title, subtitle=""))
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(content)
        return toolbar

    # ========================================================================
    # Settings page (Configuracoes)
    # ========================================================================

    def _build_settings_page(self) -> Gtk.Widget:
        """Pagina Configuracoes com abas (ViewSwitcher).

        Estrutura:
          ToolbarView
            HeaderBar (com X de fechar) + ViewSwitcher no titulo
            ViewStack
              [Aplicacao] [Seguranca] [Sobre]

        Cada aba e um Adw.PreferencesPage isolado, pra facilitar
        adicionar futuras abas (ex: Tema, Notificacoes).
        """
        # Carrega state atual (sincroniza com .desktop file caso user tenha
        # editado manualmente)
        self._settings = load_settings()
        disk_autostart = autostart_is_enabled()
        if disk_autostart != self._settings.autostart:
            self._settings.autostart = disk_autostart
            save_settings(self._settings)

        # ============= ViewStack (uma page por aba) ============= #
        stack = Adw.ViewStack()
        stack.add_titled_with_icon(
            self._build_settings_app_tab(),
            "app",
            "Aplicacao",
            "system-run-symbolic",
        )
        stack.add_titled_with_icon(
            self._build_settings_security_tab(),
            "security",
            "Seguranca",
            "channel-secure-symbolic",
        )
        stack.add_titled_with_icon(
            self._build_settings_about_tab(),
            "about",
            "Sobre",
            "help-about-symbolic",
        )

        # ============= HeaderBar com ViewSwitcher ============= #
        switcher = Adw.ViewSwitcher()
        switcher.set_stack(stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)

        header = Adw.HeaderBar()
        header.set_title_widget(switcher)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(stack)
        return toolbar

    def _build_settings_app_tab(self) -> Gtk.Widget:
        """Aba 'Aplicacao' — comportamento de inicializacao."""
        page = Adw.PreferencesPage()

        init_group = Adw.PreferencesGroup()
        init_group.set_title("Inicializacao")
        init_group.set_description(
            "Como o Hub inicia junto com o sistema."
        )

        # Switch: autostart (FUNCIONAL)
        self._sw_autostart = Adw.SwitchRow()
        self._sw_autostart.set_title("Iniciar junto com o sistema")
        self._sw_autostart.set_subtitle(
            "Cria ~/.config/autostart/vigia-hub.desktop (XDG padrao)."
        )
        self._sw_autostart.set_active(self._settings.autostart)
        self._sw_autostart.connect("notify::active", self._on_autostart_toggled)
        init_group.add(self._sw_autostart)

        # Switch: tray (FUNCIONAL — spawna subprocess GTK3)
        self._sw_tray = Adw.SwitchRow()
        self._sw_tray.set_title("Mostrar icone na bandeja do sistema")
        self._sw_tray.set_subtitle(
            "Icone perto do menu do GNOME, com menu rapido (Abrir / "
            "Configuracoes / Sair). Requer extensao AppIndicator."
        )
        self._sw_tray.set_active(self._settings.show_tray)
        self._sw_tray.connect("notify::active", self._on_tray_toggled)
        init_group.add(self._sw_tray)

        # Switch: iniciar minimizado (FUNCIONAL — depende do tray)
        self._sw_minimized = Adw.SwitchRow()
        self._sw_minimized.set_title("Iniciar minimizado na bandeja")
        self._sw_minimized.set_subtitle(
            "Inicia sem mostrar a janela — so o icone na bandeja. "
            "Requer 'Mostrar icone na bandeja' habilitado."
        )
        self._sw_minimized.set_active(self._settings.start_minimized)
        self._sw_minimized.set_sensitive(self._settings.show_tray)
        self._sw_minimized.connect("notify::active", self._on_minimized_toggled)
        init_group.add(self._sw_minimized)

        page.add(init_group)
        return page

    def _build_settings_security_tab(self) -> Gtk.Widget:
        """Aba 'Seguranca' — protecao do Hub e tools."""
        page = Adw.PreferencesPage()

        sec_group = Adw.PreferencesGroup()
        sec_group.set_title("Acesso ao Hub")
        sec_group.set_description(
            "Protecao adicional para o launcher e suas configuracoes."
        )

        # Switch: password lock (placeholder Fase 2)
        self._sw_lock = Adw.SwitchRow()
        self._sw_lock.set_title("Exigir senha para abrir o Hub")
        self._sw_lock.set_subtitle(
            "Em breve (Fase 2): bloqueia o Hub atras da senha admin (Polkit)."
        )
        self._sw_lock.set_active(False)
        self._sw_lock.set_sensitive(False)
        sec_group.add(self._sw_lock)

        page.add(sec_group)
        return page

    def _build_settings_about_tab(self) -> Gtk.Widget:
        """Aba 'Sobre' — caminhos dos arquivos de configuracao."""
        page = Adw.PreferencesPage()

        info_group = Adw.PreferencesGroup()
        info_group.set_title("Arquivos de configuracao")
        info_group.set_description(
            "Onde o Hub armazena as preferencias do usuario."
        )

        info_row = Adw.ActionRow()
        info_row.set_title("Settings")
        info_row.set_subtitle(
            "~/.config/vigia-hub/settings.json (permissao 0600)"
        )
        info_row.add_prefix(
            Gtk.Image.new_from_icon_name("text-x-generic-symbolic")
        )
        info_group.add(info_row)

        autostart_row = Adw.ActionRow()
        autostart_row.set_title("Autostart")
        autostart_row.set_subtitle(
            "~/.config/autostart/vigia-hub.desktop (XDG)"
        )
        autostart_row.add_prefix(
            Gtk.Image.new_from_icon_name("system-run-symbolic")
        )
        info_group.add(autostart_row)

        page.add(info_group)

        # Grupo Versao
        ver_group = Adw.PreferencesGroup()
        ver_group.set_title("Hub")
        from . import __version__ as _ver

        ver_row = Adw.ActionRow()
        ver_row.set_title("Vigia Hub")
        ver_row.set_subtitle(f"Versao {_ver}")
        ver_row.add_prefix(
            Gtk.Image.new_from_icon_name("preferences-system-symbolic")
        )
        ver_group.add(ver_row)

        page.add(ver_group)
        return page

    def _on_autostart_toggled(self, switch: Adw.SwitchRow, *_args) -> None:
        """User toggleou autostart — atualiza .desktop file + state.json."""
        enabled = switch.get_active()
        ok = autostart_sync(
            enabled=enabled,
            minimized=self._settings.start_minimized,
        )
        if not ok:
            # Reverte switch se gravacao falhou
            switch.set_active(not enabled)
            self._show_settings_error(
                "Falha ao salvar autostart",
                "Nao foi possivel escrever em ~/.config/autostart/. "
                "Verifique permissoes da pasta.",
            )
            return
        self._settings.autostart = enabled
        save_settings(self._settings)

    def _show_settings_error(self, heading: str, body: str) -> None:
        dlg = Adw.AlertDialog(heading=heading, body=body)
        dlg.add_response("ok", "OK")
        dlg.present(self)

    # ------------- Tray switch handler -------------

    def _on_tray_toggled(self, switch: Adw.SwitchRow, *_args) -> None:
        """User toggleou o switch do tray icon."""
        enabled = switch.get_active()

        if enabled:
            # 1. Checa pre-requisitos (lib + extensao)
            check = tray_can_work()
            if not check.ok:
                # Reverte switch e mostra dialog de instalacao
                switch.set_active(False)
                self._show_tray_install_dialog(check)
                return

            # 2. Pede ao app pra spawnar o subprocess
            app = self.get_application()
            ok, err = app.enable_tray() if hasattr(app, "enable_tray") else (False, "App sem suporte")
            if not ok:
                switch.set_active(False)
                self._show_settings_error(
                    "Falha ao iniciar tray icon",
                    err or "Erro desconhecido ao spawnar vigia-hub-tray.",
                )
                return
        else:
            # Desligar tray
            app = self.get_application()
            if hasattr(app, "disable_tray"):
                app.disable_tray()
            # Se desligou tray, "iniciar minimizado" tambem perde sentido
            if self._settings.start_minimized:
                self._sw_minimized.set_active(False)

        # Salva no JSON + atualiza state em memoria
        self._settings.show_tray = enabled
        save_settings(self._settings)

        # Re-grava autostart .desktop (--minimized depende do tray)
        if self._settings.autostart:
            autostart_sync(
                enabled=True,
                minimized=self._settings.start_minimized,
            )

        # Habilita/desabilita o switch "iniciar minimizado"
        self._sw_minimized.set_sensitive(enabled)

    def _on_minimized_toggled(self, switch: Adw.SwitchRow, *_args) -> None:
        """User toggleou 'Iniciar minimizado'."""
        enabled = switch.get_active()
        self._settings.start_minimized = enabled
        save_settings(self._settings)

        # Re-grava .desktop com --minimized se autostart on
        if self._settings.autostart:
            autostart_sync(enabled=True, minimized=enabled)

    def _show_tray_install_dialog(self, check) -> None:
        """Dialog explicando o que falta pro tray funcionar."""
        body_parts = ["O tray icon precisa de 2 componentes:\n"]
        if not check.has_lib:
            body_parts.append("• <b>libayatana-appindicator-gtk3</b> (biblioteca)")
        if not check.has_extension:
            body_parts.append(
                "• <b>gnome-shell-extension-appindicator</b> (extensao GNOME)"
            )
        elif not check.ext_enabled:
            body_parts.append(
                "• A extensao AppIndicator esta instalada mas <b>desativada</b>."
            )

        if not check.has_lib or not check.has_extension:
            body_parts.append("\n\nA instalacao requer <b>reboot</b> (Silverblue overlay).")

        body = "\n".join(body_parts)

        dlg = Adw.AlertDialog(heading="Habilitar icone na bandeja")
        dlg.set_body(body)
        dlg.set_body_use_markup(True)
        dlg.add_response("cancel", "Cancelar")

        if not check.has_lib or not check.has_extension:
            dlg.add_response("install", "Instalar agora (pkexec)")
            dlg.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
        elif check.has_extension and not check.ext_enabled:
            dlg.add_response("enable", "Ativar extensao")
            dlg.set_response_appearance("enable", Adw.ResponseAppearance.SUGGESTED)

        dlg.set_default_response("cancel")
        dlg.connect("response", self._on_tray_install_response)
        dlg.present(self)

    def _on_tray_install_response(self, _dlg, response: str) -> None:
        if response == "install":
            self._run_tray_install()
        elif response == "enable":
            self._enable_tray_extension()

    def _run_tray_install(self) -> None:
        """Lanca pkexec rpm-ostree install em background."""
        import subprocess
        cmd = install_command()
        try:
            subprocess.Popen(cmd)
            self._show_settings_error(
                "Instalacao iniciada",
                "Acompanhe a senha de admin (pkexec). Ao terminar, "
                "<b>reinicie o sistema</b> pra a biblioteca ficar disponivel. "
                "Depois ative a extensao e religue o switch.",
            )
        except OSError as e:
            self._show_settings_error(
                "Falha ao chamar pkexec",
                f"{e}\n\nComando: {' '.join(cmd)}",
            )

    def _enable_tray_extension(self) -> None:
        """Ativa extensao GNOME AppIndicator via gnome-extensions enable."""
        import subprocess
        cmd = enable_extension_command()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self._show_settings_error(
                    "Extensao ativada",
                    "AppIndicator foi ativada. Religue o switch 'Mostrar icone'.",
                )
            else:
                err = result.stderr.strip() or "Erro desconhecido."
                self._show_settings_error("Falha ao ativar extensao", err)
        except (subprocess.SubprocessError, OSError) as e:
            self._show_settings_error("Falha ao executar gnome-extensions", str(e))

    # ------------- Navigation API (chamada pelo tray via app actions) -------------

    def show_settings_view(self) -> None:
        """Navega pro modo 'settings' (chamado por app.show-settings action)."""
        # Acha a row do nav que tem mode_id='settings'
        n = self._nav_list.get_n_items() if hasattr(self._nav_list, "get_n_items") else None
        # Itera rows e seleciona a 'settings'
        idx = 0
        while True:
            row = self._nav_list.get_row_at_index(idx)
            if row is None:
                break
            if getattr(row, "_mode_id", None) == "settings":
                self._nav_list.select_row(row)
                return
            idx += 1

    # ========================================================================
    # Tools view (master-detail com categorias)
    # ========================================================================

    def _build_tools_view(self) -> Gtk.Widget:
        """Adw.NavigationSplitView: sidebar com categorias + content stack."""
        sidebar_page = self._build_sidebar()

        # Content stack
        self._content_stack = Gtk.Stack()
        self._content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._content_stack.set_transition_duration(180)

        for tool in TOOLS:
            detail = self._build_detail_page(tool)
            self._content_stack.add_named(detail, self._detail_name(tool.id))

        if not TOOLS:
            self._content_stack.add_named(
                Adw.StatusPage(
                    title="Sem ferramentas registradas",
                    description="Adicione entradas em registry.py.",
                    icon_name="dialog-information-symbolic",
                ),
                "_empty_",
            )

        content_toolbar = Adw.ToolbarView()
        content_toolbar.set_content(self._content_stack)
        content_page = Adw.NavigationPage(
            title="Vigia Suite",
            child=content_toolbar,
        )
        content_page.set_tag("content")

        split = Adw.NavigationSplitView()
        split.set_sidebar(sidebar_page)
        split.set_content(content_page)
        split.set_sidebar_width_fraction(0.28)
        split.set_min_sidebar_width(280)
        split.set_max_sidebar_width(360)
        return split

    def _build_sidebar(self) -> Adw.NavigationPage:
        """Sidebar com tools agrupadas por categoria."""
        header = Adw.HeaderBar()
        title = Adw.WindowTitle(title="Vigia Suite", subtitle="Toolkit")
        header.set_title_widget(title)

        self._sidebar_list = Gtk.ListBox()
        self._sidebar_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._sidebar_list.add_css_class("navigation-sidebar")
        self._sidebar_list.connect("row-selected", self._on_sidebar_selected)

        # Adiciona rows agrupadas por categoria, com headers separadores
        grouped = tools_by_category(TOOLS)
        for cat, tools_in_cat in grouped.items():
            # Header row (nao selecionavel)
            header_row = Gtk.ListBoxRow()
            header_row.set_selectable(False)
            header_row.set_activatable(False)
            header_row.add_css_class("dim-label")
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            hbox.set_margin_top(14)
            hbox.set_margin_bottom(4)
            hbox.set_margin_start(12)
            hbox.set_margin_end(12)
            hlbl = Gtk.Label(label=CATEGORY_LABELS.get(cat, cat).upper())
            hlbl.add_css_class("caption-heading")
            hlbl.set_xalign(0)
            hlbl.set_hexpand(True)
            hbox.append(hlbl)
            header_row.set_child(hbox)
            self._sidebar_list.append(header_row)

            for tool in tools_in_cat:
                row = self._build_sidebar_row(tool)
                self._sidebar_list.append(row)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_child(self._sidebar_list)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(scrolled)

        page = Adw.NavigationPage(title="Vigia Suite", child=toolbar)
        page.set_tag("sidebar")
        return page

    def _build_sidebar_row(self, tool: ToolEntry) -> Gtk.ListBoxRow:
        row = Adw.ActionRow()
        row.set_title(tool.name)
        row.set_subtitle(tool.description)
        row.set_use_markup(False)
        row.set_subtitle_lines(2)

        if tool.icon_path.is_file():
            icon = Gtk.Image.new_from_file(str(tool.icon_path))
        else:
            icon = Gtk.Image.new_from_icon_name("application-x-executable-symbolic")
        icon.set_pixel_size(36)
        row.add_prefix(icon)

        available = tool.is_available()
        dot = Gtk.Label(label="●")
        dot.add_css_class("success" if available else "error")
        dot.add_css_class("caption")
        dot.set_valign(Gtk.Align.CENTER)
        row.add_suffix(dot)

        row._tool_id = tool.id  # type: ignore[attr-defined]
        return row

    def _on_sidebar_selected(
        self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None
    ) -> None:
        if row is None:
            return
        tool_id = getattr(row, "_tool_id", None)
        if not tool_id:
            return
        tool = self._tool_by_id(tool_id)
        if tool is not None:
            self._show_tool(tool)

    def _tool_by_id(self, tool_id: str) -> ToolEntry | None:
        for t in TOOLS:
            if t.id == tool_id:
                return t
        return None

    # ========================================================================
    # Show tool (embed lazy ou fallback detail)
    # ========================================================================

    def _show_tool(self, tool: ToolEntry) -> None:
        if tool.is_embeddable():
            try:
                widget = self._get_or_build_embedded(tool)
                self._content_stack.set_visible_child(widget)
                return
            except Exception as e:  # pylint: disable=broad-except
                err = "".join(traceback.format_exception_only(type(e), e)).strip()
                err_name = self._error_name(tool.id)
                existing = self._content_stack.get_child_by_name(err_name)
                if existing is not None:
                    self._content_stack.remove(existing)
                self._content_stack.add_named(
                    self._build_error_page(tool, err),
                    err_name,
                )
                self._content_stack.set_visible_child_name(err_name)
                return

        self._content_stack.set_visible_child_name(self._detail_name(tool.id))

    def _get_or_build_embedded(self, tool: ToolEntry) -> Gtk.Widget:
        if tool.id in self._embedded_widgets:
            return self._embedded_widgets[tool.id]

        if tool.embedded_module is None:
            raise RuntimeError("tool nao tem embedded_module")

        module = importlib.import_module(tool.embedded_module)
        builder = getattr(module, "build_content", None)
        if not callable(builder):
            raise RuntimeError(
                f"{tool.embedded_module}.build_content() nao encontrado"
            )

        widget = builder()
        self._content_stack.add_named(widget, self._embedded_name(tool.id))
        self._embedded_widgets[tool.id] = widget

        # PERF: forca garbage collection apos construir tool (tooltips de
        # dataclasses + closures temporarias do builder podem liberar
        # alguns MB). Tambem ajuda com fragmentation do heap Python.
        import gc
        gc.collect()

        return widget

    @staticmethod
    def _detail_name(tool_id: str) -> str:
        return f"detail::{tool_id}"

    @staticmethod
    def _embedded_name(tool_id: str) -> str:
        return f"embedded::{tool_id}"

    @staticmethod
    def _error_name(tool_id: str) -> str:
        return f"error::{tool_id}"

    # ========================================================================
    # Detail page (fallback)
    # ========================================================================

    def _build_detail_page(self, tool: ToolEntry) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        clamp = Adw.Clamp(maximum_size=720, tightening_threshold=600)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_top(32)
        box.set_margin_bottom(32)
        box.set_margin_start(32)
        box.set_margin_end(32)

        if tool.icon_path.is_file():
            icon = Gtk.Image.new_from_file(str(tool.icon_path))
        else:
            icon = Gtk.Image.new_from_icon_name("application-x-executable-symbolic")
        icon.set_pixel_size(128)
        icon.set_halign(Gtk.Align.CENTER)
        box.append(icon)

        name = Gtk.Label(label=tool.name)
        name.add_css_class("title-1")
        name.set_halign(Gtk.Align.CENTER)
        box.append(name)

        subtitle = Gtk.Label(label=tool.description)
        subtitle.add_css_class("title-4")
        subtitle.add_css_class("dim-label")
        subtitle.set_halign(Gtk.Align.CENTER)
        subtitle.set_wrap(True)
        subtitle.set_justify(Gtk.Justification.CENTER)
        subtitle.set_max_width_chars(48)
        box.append(subtitle)

        # Wrapped packages (badges) — mostra dependencias originais
        if tool.wrapped_packages:
            pkg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            pkg_box.set_halign(Gtk.Align.CENTER)
            pkg_lbl = Gtk.Label(label="Wrapper de:")
            pkg_lbl.add_css_class("dim-label")
            pkg_lbl.add_css_class("caption")
            pkg_box.append(pkg_lbl)
            for p in tool.wrapped_packages:
                pill = Gtk.Label(label=p)
                pill.add_css_class("monospace")
                pill.add_css_class("caption")
                pkg_box.append(pill)
            box.append(pkg_box)

        available = tool.is_available()
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        status_box.set_halign(Gtk.Align.CENTER)
        dot = Gtk.Label(label="●")
        dot.add_css_class("success" if available else "error")
        status_box.append(dot)
        status_lbl = Gtk.Label(
            label="Disponivel" if available else "Nao instalada"
        )
        status_lbl.add_css_class("dim-label")
        status_box.append(status_lbl)
        box.append(status_box)

        if not tool.is_embeddable():
            btn = Gtk.Button(label="Abrir externamente")
            btn.add_css_class("suggested-action" if available else "flat")
            btn.set_halign(Gtk.Align.CENTER)
            btn.set_margin_top(8)
            btn.set_margin_bottom(16)
            btn.set_sensitive(available)
            if not available:
                btn.set_label("Nao instalada")
            btn.connect("clicked", lambda _b, t=tool: self._on_launch(t))
            box.append(btn)

        if tool.long_description:
            desc_group = Adw.PreferencesGroup()
            desc_group.set_title("Sobre")
            desc_label = Gtk.Label()
            desc_label.set_markup(md_to_pango(tool.long_description))
            desc_label.set_wrap(True)
            desc_label.set_xalign(0)
            desc_label.set_selectable(True)
            desc_label.set_margin_start(12)
            desc_label.set_margin_end(12)
            desc_label.set_margin_top(12)
            desc_label.set_margin_bottom(12)
            container_row = Adw.PreferencesRow()
            container_row.set_child(desc_label)
            container_row.set_activatable(False)
            desc_group.add(container_row)
            box.append(desc_group)

        if tool.features:
            feat_group = Adw.PreferencesGroup()
            feat_group.set_title("Principais features")
            for feature in tool.features:
                row = Adw.ActionRow()
                row.set_title(md_to_pango(feature))
                row.set_use_markup(True)
                bullet = Gtk.Label(label="•")
                bullet.add_css_class("accent")
                row.add_prefix(bullet)
                feat_group.add(row)
            box.append(feat_group)

        clamp.set_child(box)
        scrolled.set_child(clamp)
        return scrolled

    def _build_error_page(self, tool: ToolEntry, error: str) -> Gtk.Widget:
        page = Adw.StatusPage(
            title=f"Falha ao carregar '{tool.name}'",
            description=(
                f"{error}\n\nVerifique se o pacote esta instalado:\n"
                f"pip install --user -e tools/{tool.id}/"
            ),
            icon_name="dialog-error-symbolic",
        )
        return page

    # ========================================================================
    # Launch externo (fallback)
    # ========================================================================

    def _on_launch(self, tool: ToolEntry) -> None:
        try:
            self._launch_tool(tool)
        except Exception as e:
            self._show_error(tool, str(e))

    def _launch_tool(self, tool: ToolEntry) -> None:
        cmd = list(tool.exec_cmd)
        if tool.needs_root:
            cmd = ["pkexec"] + cmd
        if tool.needs_terminal:
            found = find_terminal()
            if found is None:
                raise RuntimeError(
                    "Nenhum terminal encontrado (procurei: "
                    + ", ".join(b for b, _ in TERMINAL_CANDIDATES)
                    + "). Instale 'gnome-console'."
                )
            term_binary, term_args = found
            cmd = [term_binary] + term_args + cmd
        subprocess.Popen(cmd)

    def _show_error(self, tool: ToolEntry, message: str) -> None:
        dlg = Adw.AlertDialog(
            heading=f"Falha ao abrir '{tool.name}'",
            body=message,
        )
        dlg.add_response("ok", "OK")
        dlg.present(self)
