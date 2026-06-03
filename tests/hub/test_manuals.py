"""Tests pro manuals.py do Vigia Hub."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from vigia_hub import manuals


class TestConstants:
    def test_valid_kinds(self):
        assert "tecnico" in manuals.VALID_KINDS
        assert "leigo" in manuals.VALID_KINDS
        assert len(manuals.VALID_KINDS) == 2

    def test_overview_id(self):
        assert manuals.OVERVIEW_ID == "_overview"


class TestManualEntries:
    def test_has_overview_first(self):
        assert manuals.MANUAL_ENTRIES[0].tool_id == "_overview"

    def test_includes_tools_plus_overview(self):
        ids = [e.tool_id for e in manuals.MANUAL_ENTRIES]
        # Sample verificacoes
        assert "vigia-hub" in ids
        assert "antivirus" in ids
        assert "activity-log" in ids
        assert "rootkit-scanner" in ids
        assert "dashboard" in ids

    def test_entries_have_required_fields(self):
        for entry in manuals.MANUAL_ENTRIES:
            assert entry.tool_id
            assert entry.name
            assert entry.icon_name


class TestFindManualPath:
    def test_returns_none_when_not_found(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(manuals, "manual_dirs", lambda: [tmp_path])
        result = manuals.find_manual_path("nonexistent", "tecnico")
        assert result is None

    def test_finds_existing_file(self, tmp_path: Path, monkeypatch):
        (tmp_path / "tecnico").mkdir()
        target = tmp_path / "tecnico" / "test-tool.md"
        target.write_text("# Test")
        monkeypatch.setattr(manuals, "manual_dirs", lambda: [tmp_path])
        result = manuals.find_manual_path("test-tool", "tecnico")
        assert result == target

    def test_kind_matters(self, tmp_path: Path, monkeypatch):
        (tmp_path / "tecnico").mkdir()
        (tmp_path / "tecnico" / "x.md").write_text("# Tecnico")
        monkeypatch.setattr(manuals, "manual_dirs", lambda: [tmp_path])
        # leigo nao existe — None
        assert manuals.find_manual_path("x", "leigo") is None
        # tecnico existe
        assert manuals.find_manual_path("x", "tecnico") is not None


class TestLoadManual:
    def test_returns_placeholder_when_missing(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(manuals, "manual_dirs", lambda: [tmp_path])
        result = manuals.load_manual("foo", "tecnico")
        assert "preparação" in result.lower() or "preparacao" in result.lower()
        assert "foo" in result

    def test_returns_file_content(self, tmp_path: Path, monkeypatch):
        (tmp_path / "leigo").mkdir()
        (tmp_path / "leigo" / "y.md").write_text("# Hello World")
        monkeypatch.setattr(manuals, "manual_dirs", lambda: [tmp_path])
        assert manuals.load_manual("y", "leigo") == "# Hello World"


class TestBuildHtml:
    def test_returns_string(self):
        html = manuals.build_html("# Title", dark_mode=False)
        assert isinstance(html, str)
        assert "<html" in html.lower()

    def test_dark_mode_applies_class(self):
        html_dark = manuals.build_html("# X", dark_mode=True)
        html_light = manuals.build_html("# X", dark_mode=False)
        assert 'class="dark"' in html_dark
        assert 'class="dark"' not in html_light

    def test_contains_css(self):
        html = manuals.build_html("hello")
        assert "<style>" in html
        assert "--bg:" in html  # CSS variables

    def test_handles_empty_markdown(self):
        html = manuals.build_html("")
        assert isinstance(html, str)
        assert "<html" in html.lower()


class TestDetection:
    def test_markdown_lib_available_returns_bool(self):
        result = manuals.markdown_lib_available()
        assert isinstance(result, bool)

    def test_webkit_available_returns_bool(self):
        result = manuals.webkit_available()
        assert isinstance(result, bool)


class TestManualDirs:
    def test_returns_list(self):
        result = manuals.manual_dirs()
        assert isinstance(result, list)
        # Em modo dev (rodando do repo), docs/manuals deveria existir
        # Mas pode nao — depende do estado do disco. So testa que retorna list.
