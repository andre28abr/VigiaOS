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
