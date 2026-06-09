"""Tests pro theme.py do Vigia Hub (v0.6.4 — sempre segue GNOME)."""

from __future__ import annotations

from vigia_hub import theme


class TestFollowSystemTheme:
    def test_does_not_crash_without_adw(self):
        """Em mac dev (sem GTK/Adw), nao deve crashar."""
        theme.follow_system_theme()


class TestIsDarkMode:
    def test_returns_bool(self):
        """Em qualquer ambiente, retorna bool sem crashar."""
        result = theme.is_dark_mode()
        assert isinstance(result, bool)


class TestBackwardsCompat:
    def test_normalize_mode_always_returns_system(self):
        """v0.6.4: tema customizado removido — sempre 'system'."""
        assert theme.normalize_mode("system") == "system"
        assert theme.normalize_mode("light") == "system"
        assert theme.normalize_mode("dark") == "system"
        assert theme.normalize_mode("anything") == "system"
        assert theme.normalize_mode("") == "system"

    def test_apply_theme_does_not_crash(self):
        """Shim de backwards compat — apenas chama follow_system_theme."""
        theme.apply_theme("system")
        theme.apply_theme("light")
        theme.apply_theme("dark")

    def test_valid_modes_is_system_only(self):
        assert theme.VALID_MODES == ("system",)


class TestTerminalTheme:
    def test_default_ui_theme_is_padrao(self):
        from vigia_hub.settings import Settings
        assert Settings().ui_theme == "padrao"

    def test_ui_themes_constant(self):
        assert theme.UI_THEMES == ("padrao", "terminal")

    def test_terminal_css_has_palette_and_mono(self):
        css = theme.TERMINAL_CSS
        assert "#39E75F" in css           # verde-neon (accent)
        assert "monospace" in css         # fonte do terminal
        assert "window_bg_color" in css   # recolore o fundo

    def test_apply_ui_theme_headless_no_crash(self):
        # sem GTK no Mac, apply_ui_theme deve só retornar (não levantar)
        theme.apply_ui_theme("terminal")
        theme.apply_ui_theme("padrao")
        theme.apply_ui_theme("valor-invalido")  # cai pra padrao, sem erro
