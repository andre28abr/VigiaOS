"""Tests pro modulo theme.py do Vigia Hub."""

from __future__ import annotations

from vigia_hub import theme


class TestNormalizeMode:
    def test_valid_modes_pass(self):
        assert theme.normalize_mode("system") == "system"
        assert theme.normalize_mode("light") == "light"
        assert theme.normalize_mode("dark") == "dark"

    def test_invalid_returns_system(self):
        assert theme.normalize_mode("") == "system"
        assert theme.normalize_mode("foo") == "system"
        assert theme.normalize_mode("Dark") == "system"  # case sensitive
        assert theme.normalize_mode("auto") == "system"


class TestApplyTheme:
    def test_does_not_crash_without_adw(self):
        """Em mac dev (sem GTK), nao deve crashar."""
        theme.apply_theme("system")
        theme.apply_theme("light")
        theme.apply_theme("dark")


class TestConstants:
    def test_valid_modes_list(self):
        assert "system" in theme.VALID_MODES
        assert "light" in theme.VALID_MODES
        assert "dark" in theme.VALID_MODES
        assert len(theme.VALID_MODES) == 3
