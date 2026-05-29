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
import threading
import traceback
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from vigia_common.helpers import show_error, show_info

from .markdown import md_to_pango
from .registry import (
    CATEGORY_LABELS,
    TOOLS,
    ToolEntry,
    tools_by_category,
    visible_tools,
)
from .auth import (
    check_auth_async,
    pkexec_available,
)
from .idle import IdleMonitor
from .logging_setup import get_logger
from .manuals import (
    MANUAL_ENTRIES,
    ManualEntry,
    build_html,
    load_manual,
    webkit_available,
)
from .theme import is_dark_mode as _theme_is_dark


_log = get_logger("vigia_hub.window")
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
        self.set_title("Vigia Hub")
        self.set_default_size(1340, 820)

        # Cache de widgets embarcados (tools): tool.id -> Gtk.Widget
        self._embedded_widgets: dict[str, Gtk.Widget] = {}
        # Caches de paginas de modo (installer, settings, help)
        self._mode_pages: dict[str, Gtk.Widget] = {}
        # Idle monitor (auto-lock) — None ate ser configurado
        self._idle_monitor = None
        # Handler ID do switch de lock (pra block/unblock anti-recursao)
        self._sw_lock_handler_id = 0
        # Settings — carregado lazy quando aba Config abre. Pre-carrega aqui
        # pra _reconfigure_idle_monitor() funcionar caso lock ja' estivesse on
        self._settings = load_settings()

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

        # Inicializa idle monitor se config diz pra ativar (lock + minutes>0)
        self._reconfigure_idle_monitor()

        # Listener pra mudancas de tema do GNOME (light <-> dark) —
        # re-renderiza manuais em tempo real sem precisar reabrir o Hub
        try:
            sm = Adw.StyleManager.get_default()
            sm.connect("notify::dark", self._on_system_theme_changed)
        except Exception as e:  # pylint: disable=broad-except
            _log.debug("nao conseguiu conectar listener de tema: %s", e)

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
        header_lbl = Gtk.Label(label="Vigia Hub")
        header_lbl.add_css_class("caption-heading")
        header_lbl.add_css_class("dim-label")
        header_lbl.set_wrap(True)
        header_lbl.set_justify(Gtk.Justification.CENTER)
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
            return self._build_help_page()
        raise ValueError(f"Modo desconhecido: {mode_id}")

    def _build_help_page(self) -> Gtk.Widget:
        """Aba Ajuda: 3 sub-abas (ViewSwitcher) com manuais.

        - Visao geral: ExpanderRows com descricao curta (do registry)
        - Manual tecnico: WebKit renderiza docs/manuals/tecnico/<tool>.md
        - Manual simples: WebKit renderiza docs/manuals/leigo/<tool>.md

        Estrutura:
          ToolbarView
            HeaderBar (com X) + ViewSwitcher
            ViewStack
              ├── overview -> PreferencesPage com ExpanderRows
              ├── tecnico  -> SplitView (sidebar tools + WebKit content)
              └── leigo    -> SplitView (sidebar tools + WebKit content)
        """
        stack = Adw.ViewStack()
        stack.add_titled_with_icon(
            self._build_help_overview_tab(),
            "overview",
            "Visão geral",
            "view-list-symbolic",
        )
        stack.add_titled_with_icon(
            self._build_help_manual_tab("tecnico"),
            "tecnico",
            "Manual técnico",
            "utilities-terminal-symbolic",
        )
        stack.add_titled_with_icon(
            self._build_help_manual_tab("leigo"),
            "leigo",
            "Manual para leigos",
            "user-info-symbolic",
        )

        switcher = Adw.ViewSwitcher()
        switcher.set_stack(stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)

        header = Adw.HeaderBar()
        header.set_title_widget(switcher)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(stack)
        return toolbar

    def _build_help_overview_tab(self) -> Gtk.Widget:
        """Aba 'Visão geral' — ExpanderRows por categoria (versao antiga)."""
        page = Adw.PreferencesPage()

        intro_group = Adw.PreferencesGroup()
        intro_group.set_title("Manual do VigiaOS")
        intro_group.set_description(
            "Resumo rapido de cada ferramenta. Para detalhes tecnicos ou "
            "explicacao em linguagem simples, use as outras abas acima."
        )
        page.add(intro_group)

        grouped = tools_by_category(visible_tools())
        for cat, tools_in_cat in grouped.items():
            group = Adw.PreferencesGroup()
            group.set_title(CATEGORY_LABELS.get(cat, cat))

            for tool in tools_in_cat:
                expander = Adw.ExpanderRow()
                expander.set_title(tool.name)
                expander.set_subtitle(tool.description)
                if tool.icon_path.is_file():
                    icon = Gtk.Image.new_from_file(str(tool.icon_path))
                else:
                    icon = Gtk.Image.new_from_icon_name(
                        "application-x-executable-symbolic"
                    )
                icon.set_pixel_size(36)
                expander.add_prefix(icon)

                body_box = Gtk.Box(
                    orientation=Gtk.Orientation.VERTICAL, spacing=12
                )
                body_box.set_margin_top(12)
                body_box.set_margin_bottom(12)
                body_box.set_margin_start(16)
                body_box.set_margin_end(16)

                if tool.long_description:
                    desc_lbl = Gtk.Label()
                    desc_lbl.set_markup(md_to_pango(tool.long_description))
                    desc_lbl.set_wrap(True)
                    desc_lbl.set_xalign(0)
                    desc_lbl.set_selectable(True)
                    body_box.append(desc_lbl)

                if tool.features:
                    feat_header = Gtk.Label(label="Principais features:")
                    feat_header.add_css_class("caption-heading")
                    feat_header.set_xalign(0)
                    feat_header.set_margin_top(6)
                    body_box.append(feat_header)
                    for feature in tool.features:
                        row = Gtk.Box(
                            orientation=Gtk.Orientation.HORIZONTAL, spacing=8
                        )
                        bullet = Gtk.Label(label="•")
                        bullet.add_css_class("accent")
                        bullet.set_valign(Gtk.Align.START)
                        row.append(bullet)
                        text = Gtk.Label()
                        text.set_markup(md_to_pango(feature))
                        text.set_wrap(True)
                        text.set_xalign(0)
                        text.set_hexpand(True)
                        row.append(text)
                        body_box.append(row)

                wrapper = Adw.PreferencesRow()
                wrapper.set_activatable(False)
                wrapper.set_child(body_box)
                expander.add_row(wrapper)

                group.add(expander)

            page.add(group)

        return page

    def _build_help_manual_tab(self, kind: str) -> Gtk.Widget:
        """Aba 'Manual tecnico' ou 'Manual simples'.

        SplitView: sidebar com lista de tools + content com WebKit
        renderizando o .md selecionado.
        """
        # ============= Sidebar (lista de tools) ============= #
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        listbox.add_css_class("navigation-sidebar")

        for entry in MANUAL_ENTRIES:
            row = Adw.ActionRow()
            row.set_title(entry.name)
            row.set_use_markup(False)
            icon = Gtk.Image.new_from_icon_name(entry.icon_name)
            icon.set_pixel_size(24)
            row.add_prefix(icon)
            row._manual_id = entry.tool_id  # type: ignore[attr-defined]
            listbox.append(row)

        scrolled_side = Gtk.ScrolledWindow()
        scrolled_side.set_policy(
            Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC
        )
        scrolled_side.set_child(listbox)
        scrolled_side.set_vexpand(True)

        sidebar_toolbar = Adw.ToolbarView()
        sidebar_header = Adw.HeaderBar()
        sidebar_header.set_show_back_button(False)
        # Sem window-controls (X) aqui: este SplitView fica DENTRO da aba
        # Ajuda, cujo header externo (com o ViewSwitcher) ja' carrega o X.
        # Mostrar de novo gerava o "botao de fechar duplicado".
        sidebar_header.set_show_start_title_buttons(False)
        sidebar_header.set_show_end_title_buttons(False)
        sidebar_header.set_title_widget(Adw.WindowTitle(
            title="Ferramentas", subtitle=""
        ))
        sidebar_toolbar.add_top_bar(sidebar_header)
        sidebar_toolbar.set_content(scrolled_side)
        sidebar_page = Adw.NavigationPage.new(sidebar_toolbar, "Ferramentas")

        # ============= Content (WebKit ou fallback) ============= #
        content_holder = Gtk.Stack()  # vamos trocar children conforme tool
        content_holder.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        content_holder.set_transition_duration(150)
        content_holder.set_vexpand(True)
        content_holder.set_hexpand(True)

        # Initial: empty state
        empty = Adw.StatusPage(
            title="Selecione uma ferramenta",
            description=(
                "Escolha uma ferramenta na lista para ver o manual."
            ),
            icon_name="help-browser-symbolic",
        )
        content_holder.add_named(empty, "_empty")

        content_toolbar = Adw.ToolbarView()
        content_header = Adw.HeaderBar()
        # Idem sidebar_header: sem X aqui (era o botao de fechar duplicado
        # que aparecia ao abrir um manual). So' o header externo da aba
        # Ajuda mantem os window-controls.
        content_header.set_show_start_title_buttons(False)
        content_header.set_show_end_title_buttons(False)
        content_header.set_title_widget(Adw.WindowTitle(
            title=(
                "Manual técnico" if kind == "tecnico"
                else "Manual simples"
            ),
            subtitle="",
        ))
        content_toolbar.add_top_bar(content_header)
        content_toolbar.set_content(content_holder)
        content_nav = Adw.NavigationPage.new(content_toolbar, "Manual")

        # Wire listbox selection -> render manual
        # Use closure pra capturar kind + content_holder + content_header
        def on_row_selected(_lb, row):
            if row is None:
                return
            tool_id = getattr(row, "_manual_id", None)
            if not tool_id:
                return
            # Atualiza header title pra incluir nome da tool
            entry = next(
                (e for e in MANUAL_ENTRIES if e.tool_id == tool_id),
                None,
            )
            if entry is not None:
                title_widget = content_header.get_title_widget()
                if hasattr(title_widget, "set_subtitle"):
                    title_widget.set_subtitle(entry.name)
            # Renderiza manual na tool
            self._render_manual_into(content_holder, tool_id, kind)

        listbox.connect("row-selected", on_row_selected)

        # Seleciona _overview por default
        first_row = listbox.get_row_at_index(0)
        if first_row is not None:
            listbox.select_row(first_row)

        # ============= Split layout ============= #
        split = Adw.NavigationSplitView()
        split.set_sidebar(sidebar_page)
        split.set_content(content_nav)
        split.set_sidebar_width_fraction(0.30)
        split.set_min_sidebar_width(240)
        split.set_max_sidebar_width(320)
        return split

    def _render_manual_into(
        self, container: Gtk.Stack, tool_id: str, kind: str
    ) -> None:
        """Renderiza o manual da tool no container Stack.

        OTIMIZACAO v0.6.3: reusa 1 unico WebView por aba (tecnico/leigo)
        em vez de criar 1 por tool. WebView e' caro de criar em VM
        (UTM/QEMU); reuso reduz drasticamente latencia de click.

        load_html() em WebView ja' renderizado e' praticamente
        instantaneo — so o primeiro click numa aba paga o custo de
        criar o widget.
        """
        # Cache do WebView ativo pra aba + tracking do tool atual
        # pra re-renderizar quando o tema GNOME mudar
        if not hasattr(self, "_manual_webviews"):
            self._manual_webviews = {}  # kind -> WebKit.WebView
        if not hasattr(self, "_manual_fallbacks"):
            self._manual_fallbacks = {}  # kind -> Gtk.ScrolledWindow
        if not hasattr(self, "_manual_current"):
            self._manual_current = {}  # kind -> tool_id ativo

        self._manual_current[kind] = tool_id
        markdown_text = load_manual(tool_id, kind)  # type: ignore[arg-type]

        # Tenta WebKit primeiro (reusa instancia por aba)
        if webkit_available():
            view = self._manual_webviews.get(kind)
            if view is None:
                view = self._create_webview()
                if view is not None:
                    self._manual_webviews[kind] = view
                    container.add_named(view, f"{kind}::webview")

            if view is not None:
                # Detecta tema atual pra CSS dark/light
                dark = self._is_dark_mode()
                html = build_html(markdown_text, dark_mode=dark)
                view.load_html(html, None)
                container.set_visible_child(view)
                return

        # Fallback: TextView reusado
        scrolled = self._manual_fallbacks.get(kind)
        if scrolled is None:
            scrolled, buf = self._create_text_fallback()
            self._manual_fallbacks[kind] = scrolled
            scrolled._buffer = buf  # type: ignore[attr-defined]
            container.add_named(scrolled, f"{kind}::fallback")

        scrolled._buffer.set_text(markdown_text)  # type: ignore[attr-defined]
        container.set_visible_child(scrolled)

    def _on_system_theme_changed(self, *_args) -> None:
        """User mudou tema do GNOME — re-renderiza manuais ativos."""
        _log.info("tema GNOME mudou (dark=%s) — re-renderiza manuais",
                  self._is_dark_mode())
        if not hasattr(self, "_manual_webviews"):
            return
        dark = self._is_dark_mode()
        for kind, view in self._manual_webviews.items():
            tool_id = self._manual_current.get(kind)
            if tool_id is None:
                continue
            try:
                markdown_text = load_manual(tool_id, kind)  # type: ignore[arg-type]
                html = build_html(markdown_text, dark_mode=dark)
                view.load_html(html, None)
            except Exception as e:  # pylint: disable=broad-except
                _log.warning("re-render manual falhou (%s/%s): %s",
                             kind, tool_id, e)

    @staticmethod
    def _is_dark_mode() -> bool:
        """True se Adw esta renderizando em dark (segue tema GNOME)."""
        return _theme_is_dark()

    def _create_webview(self):
        """Cria UM WebKit.WebView novo. Retorna None se falhar."""
        try:
            import gi
            gi.require_version("WebKit", "6.0")
            from gi.repository import WebKit
            view = WebKit.WebView()
            view.set_vexpand(True)
            view.set_hexpand(True)
            # Settings: desabilita JS pra reduzir overhead (manuais sao
            # estaticos), mantem zoom default
            try:
                settings = view.get_settings()
                settings.set_enable_javascript(False)
                settings.set_enable_smooth_scrolling(True)
            except Exception:  # pylint: disable=broad-except
                pass
            return view
        except Exception as e:  # pylint: disable=broad-except
            _log.warning("WebKit init falhou: %s", e)
            return None

    @staticmethod
    def _create_text_fallback():
        """Cria TextView dentro de ScrolledWindow. Retorna (scrolled, buffer)."""
        buf = Gtk.TextBuffer()
        text_view = Gtk.TextView(buffer=buf)
        text_view.set_editable(False)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text_view.set_left_margin(24)
        text_view.set_right_margin(24)
        text_view.set_top_margin(24)
        text_view.set_bottom_margin(24)
        text_view.set_monospace(True)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )
        scrolled.set_child(text_view)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        return scrolled, buf

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
        # Re-carrega state atual (caso user tenha editado entre aberturas)
        # e sincroniza com .desktop file
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

        # Grupo: backup e restauracao (Etapa D)
        backup_group = Adw.PreferencesGroup()
        backup_group.set_title("Backup e restauração")
        backup_group.set_description(
            "Salva configurações e relatórios num arquivo .zip protegido "
            "(permissão 0600 — LGPD)."
        )

        backup_row = Adw.ActionRow()
        backup_row.set_title("Criar backup")
        backup_row.set_subtitle(
            "Gera um .zip com configurações + relatórios de scan."
        )
        self._backup_btn = Gtk.Button(label="Criar backup")
        self._backup_btn.add_css_class("suggested-action")
        self._backup_btn.set_valign(Gtk.Align.CENTER)
        self._backup_btn.connect("clicked", self._on_create_backup)
        backup_row.add_suffix(self._backup_btn)
        backup_group.add(backup_row)

        restore_row = Adw.ActionRow()
        restore_row.set_title("Restaurar backup")
        restore_row.set_subtitle(
            "Recupera config + relatórios de um .zip criado pela Vigia."
        )
        self._restore_btn = Gtk.Button(label="Restaurar…")
        self._restore_btn.set_valign(Gtk.Align.CENTER)
        self._restore_btn.connect("clicked", self._on_restore_backup)
        restore_row.add_suffix(self._restore_btn)
        backup_group.add(restore_row)

        page.add(backup_group)

        # NOTA v0.6.4: removido grupo "Aparencia" (tema light/dark
        # customizado). Hub agora sempre segue o tema do GNOME — se
        # o usuario quer escuro, configura em Configuracoes > Aparencia
        # do proprio GNOME. Reduz superficie de configuracao e mantem
        # consistencia visual com o resto do desktop.

        return page

    def _build_settings_security_tab(self) -> Gtk.Widget:
        """Aba 'Seguranca' — protecao do Hub e tools."""
        page = Adw.PreferencesPage()

        sec_group = Adw.PreferencesGroup()
        sec_group.set_title("Acesso ao Hub")
        sec_group.set_description(
            "Protecao adicional para o launcher e suas configuracoes."
        )

        # Switch: password lock (FUNCIONAL — pkexec via Gio.Subprocess async)
        self._sw_lock = Adw.SwitchRow()
        self._sw_lock.set_title("Exigir senha para abrir o Hub")
        self._sw_lock.set_subtitle(self._lock_default_subtitle())
        self._sw_lock.set_active(self._settings.password_lock)
        # IMPORTANTE: armazena handler_id pra poder block/unblock e evitar
        # recursao quando re-setar active programaticamente
        self._sw_lock_handler_id = self._sw_lock.connect(
            "notify::active", self._on_lock_toggled
        )
        sec_group.add(self._sw_lock)

        # Auto-lock por inatividade — combo de minutos
        self._autolock_row = Adw.ComboRow()
        self._autolock_row.set_title("Auto-bloquear apos inatividade")
        self._autolock_row.set_subtitle(
            "Esconde a janela e exige senha de novo na proxima abertura. "
            "Mede inatividade da janela do Hub."
        )
        autolock_model = Gtk.StringList.new([
            "Desativado", "5 minutos", "10 minutos", "15 minutos",
            "30 minutos", "60 minutos",
        ])
        self._autolock_values = [0, 5, 10, 15, 30, 60]
        self._autolock_row.set_model(autolock_model)
        try:
            current_idx = self._autolock_values.index(self._settings.auto_lock_minutes)
        except ValueError:
            current_idx = 0
        self._autolock_row.set_selected(current_idx)
        # Sensitive: so faz sentido com lock ativo
        self._autolock_row.set_sensitive(self._settings.password_lock)
        self._autolock_row.connect("notify::selected", self._on_autolock_changed)
        sec_group.add(self._autolock_row)

        page.add(sec_group)

        # Grupo info
        info_group = Adw.PreferencesGroup()
        info_group.set_title("Como funciona")
        info_group.set_description(
            "Bloqueio reutiliza a infraestrutura nativa do Linux."
        )

        polkit_row = Adw.ActionRow()
        polkit_row.set_title("pkexec / Polkit")
        polkit_row.set_subtitle(
            "Framework de autorizacao padrao do Linux. Reutiliza PAM e a "
            "senha do sudo. Sem armazenamento local (LGPD compliant)."
        )
        polkit_row.add_prefix(
            Gtk.Image.new_from_icon_name("channel-secure-symbolic")
        )
        info_group.add(polkit_row)

        page.add(info_group)
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

    # ------------------------------------------------------------------
    # Backup / restauracao (Etapa D) — backend em backup.py (testavel)
    # ------------------------------------------------------------------

    def _on_create_backup(self, _btn: Gtk.Button) -> None:
        from .backup import BACKUP_DIR, default_backup_name

        dlg = Gtk.FileDialog()
        dlg.set_title("Salvar backup da Vigia")
        dlg.set_initial_name(default_backup_name())
        try:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            dlg.set_initial_folder(Gio.File.new_for_path(str(BACKUP_DIR)))
        except OSError:
            pass
        dlg.save(self, None, self._on_backup_dest_chosen)

    def _on_backup_dest_chosen(
        self, dlg: Gtk.FileDialog, result: Gio.AsyncResult
    ) -> None:
        try:
            gfile = dlg.save_finish(result)
        except GLib.Error:
            return  # usuario cancelou
        if gfile is None:
            return
        dest = gfile.get_path()
        if not dest:
            return

        self._backup_btn.set_sensitive(False)

        def worker() -> None:
            from .backup import create_backup
            ok, msg, path = create_backup(Path(dest))
            GLib.idle_add(
                self._on_backup_done, ok, msg, str(path) if path else ""
            )

        threading.Thread(target=worker, daemon=True).start()

    def _on_backup_done(self, ok: bool, msg: str, path: str) -> bool:
        self._backup_btn.set_sensitive(True)
        if ok:
            body = msg
            if path:
                body += f"\n\n{path}"
            show_info(self, "Backup criado", body)
        else:
            show_error(self, "Falha no backup", msg)
        return False  # remove do idle

    def _on_restore_backup(self, _btn: Gtk.Button) -> None:
        from .backup import BACKUP_DIR

        dlg = Gtk.FileDialog()
        dlg.set_title("Escolher backup para restaurar")
        filt = Gtk.FileFilter()
        filt.set_name("Backup Vigia (*.zip)")
        filt.add_pattern("*.zip")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filt)
        dlg.set_filters(filters)
        if BACKUP_DIR.is_dir():
            dlg.set_initial_folder(Gio.File.new_for_path(str(BACKUP_DIR)))
        dlg.open(self, None, self._on_restore_src_chosen)

    def _on_restore_src_chosen(
        self, dlg: Gtk.FileDialog, result: Gio.AsyncResult
    ) -> None:
        try:
            gfile = dlg.open_finish(result)
        except GLib.Error:
            return
        if gfile is None:
            return
        src = gfile.get_path()
        if not src:
            return

        confirm = Adw.AlertDialog(
            heading="Restaurar este backup?",
            body=(
                "As configurações e relatórios atuais serão substituídos "
                "pelos do backup. Esta ação não pode ser desfeita."
            ),
        )
        confirm.add_response("cancel", "Cancelar")
        confirm.add_response("restore", "Restaurar")
        confirm.set_response_appearance(
            "restore", Adw.ResponseAppearance.DESTRUCTIVE
        )
        confirm.set_default_response("cancel")
        confirm.connect("response", self._on_restore_confirmed, src)
        confirm.present(self)

    def _on_restore_confirmed(
        self, _dlg: Adw.AlertDialog, response: str, src: str
    ) -> None:
        if response != "restore":
            return
        self._restore_btn.set_sensitive(False)

        def worker() -> None:
            from .backup import restore_backup
            ok, msg, labels = restore_backup(Path(src))
            GLib.idle_add(self._on_restore_done, ok, msg, labels)

        threading.Thread(target=worker, daemon=True).start()

    def _on_restore_done(
        self, ok: bool, msg: str, labels: list[str]
    ) -> bool:
        self._restore_btn.set_sensitive(True)
        if ok:
            body = msg
            if labels:
                body += "\n\n" + "\n".join(f"• {label}" for label in labels)
            body += "\n\nReinicie o Hub para aplicar todas as mudanças."
            show_info(self, "Backup restaurado", body)
        else:
            show_error(self, "Falha ao restaurar", msg)
        return False

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
        """Lanca o install dos pacotes do tray em background (rpm-ostree
        em sistema atomico, dnf no Workstation)."""
        import subprocess
        from vigia_common.platform import needs_reboot_to_apply
        cmd = install_command()
        try:
            subprocess.Popen(cmd)
            if needs_reboot_to_apply():
                msg = (
                    "Acompanhe a senha de admin (pkexec). Ao terminar, "
                    "<b>reinicie o sistema</b> pra a biblioteca ficar "
                    "disponivel. Depois ative a extensao e religue o switch."
                )
            else:
                msg = (
                    "Acompanhe a senha de admin (pkexec). Ao terminar, ative "
                    "a extensao AppIndicator e religue o switch (sem reboot)."
                )
            self._show_settings_error("Instalacao iniciada", msg)
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

    # ------------- Password lock switch (pkexec async) -------------
    #
    # v0.5.9 — Reescrito: usa Gio.Subprocess (async no GMainLoop) ao
    # inves de threading.Thread + Polkit lib. Motivos:
    #
    # 1. Polkit lib do PyGObject NAO e' thread-safe (deadlock D-Bus).
    # 2. Threads bagunca o D-Bus do Adw.Application.
    # 3. Gio.Subprocess e' native async — sem threads, sem deadlock.
    # 4. pkexec /usr/bin/true ja' dispara o prompt do Polkit nativo.
    # 5. Sem necessidade de .policy custom — usa action default.
    #
    # Bonus: handler_block_by_func evita recursao quando setamos
    # active=False programaticamente apos falha.

    def _set_lock_switch_quietly(self, value: bool) -> None:
        """Muda valor do switch SEM disparar o handler de notify::active.

        Evita recursao infinita quando revertemos o switch apos erro.
        """
        if self._sw_lock_handler_id:
            self._sw_lock.handler_block(self._sw_lock_handler_id)
        self._sw_lock.set_active(value)
        if self._sw_lock_handler_id:
            self._sw_lock.handler_unblock(self._sw_lock_handler_id)

    def _on_lock_toggled(self, switch: Adw.SwitchRow, *_args) -> None:
        """User toggleou 'Exigir senha para abrir o Hub'.

        Fluxo unico (ligar ou desligar): dispara pkexec via Gio.Subprocess
        async. O dialog de senha aparece nativo do GNOME. Quando user
        responde, callback ajusta switch + salva.
        """
        target = switch.get_active()
        _log.debug("lock toggled target=%s", target)

        if not pkexec_available():
            self._set_lock_switch_quietly(not target)
            self._show_settings_error(
                "pkexec nao disponivel",
                "O comando 'pkexec' nao foi encontrado no sistema. "
                "Pacote: polkit (geralmente ja' vem instalado).",
            )
            return

        # Feedback visual sutil enquanto async roda — sem dialog modal
        switch.set_sensitive(False)
        switch.set_subtitle(
            "Aguardando autenticacao... (digite a senha admin no prompt)"
        )

        def on_result(ok: bool, err: str) -> None:
            _log.debug("lock auth result: ok=%s err=%r", ok, err)
            switch.set_sensitive(True)
            switch.set_subtitle(self._lock_default_subtitle())

            if not ok:
                # Reverte switch SEM disparar handler (anti-recursao)
                self._set_lock_switch_quietly(not target)
                self._show_settings_error(
                    "Autenticacao falhou",
                    err or "Senha incorreta ou prompt cancelado. "
                           "O bloqueio nao foi alterado.",
                )
                return

            # Autenticou — salva no JSON
            self._settings.password_lock = target
            save_settings(self._settings)
            app = self.get_application()
            if hasattr(app, "_authed"):
                app._authed = True  # type: ignore[attr-defined]
            _log.info("password_lock saved=%s", target)
            # Auto-lock so faz sentido com lock on
            if hasattr(self, "_autolock_row"):
                self._autolock_row.set_sensitive(target)
            # Reconfigura monitor de idle se foi habilitado
            self._reconfigure_idle_monitor()

        # Dispara pkexec via Gio.Subprocess async (sem threads)
        check_auth_async(on_result)

    @staticmethod
    def _lock_default_subtitle() -> str:
        return (
            "Pede senha admin (mesma do sudo) ao iniciar o Hub. Usa Polkit "
            "do sistema — nenhuma senha e' armazenada pelo Vigia."
        )

    # ------------- Auto-lock handler -------------

    def _on_autolock_changed(self, combo: Adw.ComboRow, *_args) -> None:
        idx = combo.get_selected()
        if 0 <= idx < len(self._autolock_values):
            minutes = self._autolock_values[idx]
        else:
            minutes = 0
        self._settings.auto_lock_minutes = minutes
        save_settings(self._settings)
        _log.info("auto_lock_minutes set to %s", minutes)
        self._reconfigure_idle_monitor()

    def _reconfigure_idle_monitor(self) -> None:
        """(Re)Inicializa monitor de inatividade conforme settings atuais.

        So ativa se:
        - password_lock ESTA habilitado
        - auto_lock_minutes > 0
        Caso contrario, para o monitor existente.
        """
        # Para o monitor antigo (se existe)
        existing = getattr(self, "_idle_monitor", None)
        if existing is not None:
            existing.stop()
            self._idle_monitor = None

        if not self._settings.password_lock:
            return
        if self._settings.auto_lock_minutes <= 0:
            return

        self._idle_monitor = IdleMonitor(
            window=self,
            timeout_minutes=self._settings.auto_lock_minutes,
            on_idle=self._on_idle_timeout,
        )
        self._idle_monitor.start()
        _log.info(
            "idle monitor started: %s min",
            self._settings.auto_lock_minutes,
        )

    def _on_idle_timeout(self) -> None:
        """Callback do IdleMonitor: esconde janela + forca reauth."""
        _log.info("idle timeout — esconder janela e forcar reauth")
        # Reseta auth flag pra proxima abertura pedir senha
        app = self.get_application()
        if hasattr(app, "_authed"):
            app._authed = False  # type: ignore[attr-defined]
        # Esconde janela (se tray ON, processo continua vivo)
        self.set_visible(False)

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

    def show_tool(self, tool_id: str) -> None:
        """Navega pro modo 'tools' e seleciona a tool dada.

        Chamado por app.show-tool (acoes rapidas do tray). Selecionar a
        row da sidebar dispara _on_sidebar_selected -> _show_tool.
        """
        # 1. Garante modo 'tools' na nav fina (esquerda)
        idx = 0
        while True:
            row = self._nav_list.get_row_at_index(idx)
            if row is None:
                break
            if getattr(row, "_mode_id", None) == "tools":
                self._nav_list.select_row(row)
                break
            idx += 1
        self._main_stack.set_visible_child_name("tools")

        # 2. Seleciona a row da tool na sidebar central
        idx = 0
        while True:
            row = self._sidebar_list.get_row_at_index(idx)
            if row is None:
                break
            if getattr(row, "_tool_id", None) == tool_id:
                self._sidebar_list.select_row(row)
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

        for tool in visible_tools():
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
            title="Vigia Hub",
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
        # Branding "Vigia Hub" fica no rail (esquerda); aqui a sidebar so'
        # rotula o que ela e' (lista de ferramentas). Antes dizia
        # "Vigia Suite / Toolkit" (nome legado + redundante com o rail).
        title = Adw.WindowTitle(title="Ferramentas", subtitle="")
        header.set_title_widget(title)

        self._sidebar_list = Gtk.ListBox()
        self._sidebar_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._sidebar_list.add_css_class("navigation-sidebar")
        self._sidebar_list.connect("row-selected", self._on_sidebar_selected)

        # Adiciona rows agrupadas por categoria, com headers separadores
        grouped = tools_by_category(visible_tools())
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

        page = Adw.NavigationPage(title="Ferramentas", child=toolbar)
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
