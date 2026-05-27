"""Tests para browser_extensions.py (Vigia Tool Installer v0.2).

Cobre:
- Catalogo bem formado (campos obrigatorios)
- Detecao de browsers via shutil.which
- State local (load/save/mark/unmark)
- Lock por categoria (find_conflicts)
- URL builder pra AMO/Web Store
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from vigia_installer import browser_extensions as be


# ============================================================
# Catalogo
# ============================================================


class TestCatalog:
    def test_catalog_not_empty(self):
        assert len(be.CATALOG) > 0

    def test_all_entries_have_required_fields(self):
        for ext in be.CATALOG:
            assert ext.id
            assert ext.name
            assert ext.description
            assert ext.why
            assert ext.category
            assert ext.license
            assert ext.homepage.startswith("http")

    def test_unique_ids(self):
        ids = [e.id for e in be.CATALOG]
        assert len(ids) == len(set(ids)), "IDs duplicados no catalogo"

    def test_at_least_one_ad_blocker(self):
        ad_blockers = [e for e in be.CATALOG if e.category == "ad-blocker"]
        assert len(ad_blockers) >= 1

    def test_ublock_is_recommended(self):
        """uBlock Origin deve estar no catalogo e ser recommended."""
        ublock = be.find_extension("ublock-origin")
        assert ublock is not None
        assert ublock.recommended is True
        assert ublock.license == "GPL-3.0"

    def test_categories_have_labels(self):
        """Toda categoria usada deve ter label em CATEGORY_LABELS."""
        used = {e.category for e in be.CATALOG}
        for cat in used:
            assert cat in be.CATEGORY_LABELS, f"Categoria {cat} sem label"

    def test_exclusive_categories_subset_of_categories(self):
        used = {e.category for e in be.CATALOG}
        for cat in be.EXCLUSIVE_CATEGORIES:
            assert cat in used or cat in be.CATEGORY_LABELS

    def test_firefox_or_chrome_available_for_each_ext(self):
        """Cada extensao deve ter ao menos um dos slugs (firefox/chrome)."""
        for ext in be.CATALOG:
            has_firefox = bool(ext.firefox_slug)
            has_chrome = bool(ext.chrome_id)
            assert has_firefox or has_chrome, \
                f"{ext.id} nao tem firefox_slug nem chrome_id"


class TestBrowserList:
    def test_supported_browsers_have_required_fields(self):
        for b in be.SUPPORTED_BROWSERS:
            assert b.id
            assert b.label
            assert b.binary
            assert b.family in ("firefox", "chromium")

    def test_includes_main_browsers(self):
        ids = {b.id for b in be.SUPPORTED_BROWSERS}
        assert "firefox" in ids
        assert "chrome" in ids
        assert "brave" in ids


class TestDetectInstalledBrowsers:
    @patch("vigia_installer.browser_extensions.shutil.which")
    def test_detects_when_binary_exists(self, mock_which):
        # Simula: so firefox e chrome instalados
        def fake_which(binary):
            return f"/usr/bin/{binary}" if binary in ("firefox", "google-chrome") else None
        mock_which.side_effect = fake_which
        detected = be.detect_installed_browsers()
        ids = {b.id for b in detected}
        assert "firefox" in ids
        assert "chrome" in ids
        assert "brave" not in ids

    @patch("vigia_installer.browser_extensions.shutil.which")
    def test_no_browsers_installed(self, mock_which):
        mock_which.return_value = None
        assert be.detect_installed_browsers() == []


# ============================================================
# URL builder
# ============================================================


class TestUrlFor:
    def test_firefox_uses_amo(self):
        ublock = be.find_extension("ublock-origin")
        firefox = next(b for b in be.SUPPORTED_BROWSERS if b.id == "firefox")
        url = be.url_for(ublock, firefox)
        assert url is not None
        assert "addons.mozilla.org" in url
        assert "ublock-origin" in url

    def test_chrome_uses_web_store(self):
        ublock = be.find_extension("ublock-origin")
        chrome = next(b for b in be.SUPPORTED_BROWSERS if b.id == "chrome")
        url = be.url_for(ublock, chrome)
        assert url is not None
        assert "chromewebstore" in url or "chrome.google.com" in url

    def test_brave_uses_chrome_url(self):
        """Brave usa Chrome Web Store (familia chromium)."""
        ublock = be.find_extension("ublock-origin")
        brave = next(b for b in be.SUPPORTED_BROWSERS if b.id == "brave")
        url = be.url_for(ublock, brave)
        assert url is not None
        assert "chromewebstore" in url or "chrome.google.com" in url

    def test_returns_none_when_unavailable(self):
        """LibRedirect nao tem versao Chrome — url_for deve retornar None."""
        libredirect = be.find_extension("libredirect")
        chrome = next(b for b in be.SUPPORTED_BROWSERS if b.id == "chrome")
        url = be.url_for(libredirect, chrome)
        assert url is None


# ============================================================
# State local (mark / unmark / conflicts)
# ============================================================


class TestStateLocal:
    def setup_method(self):
        """Cada test comeca com state limpo."""
        # Patch STATE_PATH pra tmp file no setup
        pass

    def test_mark_and_get_installed(self, tmp_path, monkeypatch):
        fake_state = tmp_path / "state.json"
        monkeypatch.setattr(be, "STATE_PATH", fake_state)

        assert be.get_installed("ublock-origin") == []
        be.mark_installed("ublock-origin", "firefox")
        assert "firefox" in be.get_installed("ublock-origin")

    def test_is_marked_installed(self, tmp_path, monkeypatch):
        fake_state = tmp_path / "state.json"
        monkeypatch.setattr(be, "STATE_PATH", fake_state)

        assert not be.is_marked_installed("ublock-origin", "firefox")
        be.mark_installed("ublock-origin", "firefox")
        assert be.is_marked_installed("ublock-origin", "firefox")
        assert not be.is_marked_installed("ublock-origin", "chrome")

    def test_unmark(self, tmp_path, monkeypatch):
        fake_state = tmp_path / "state.json"
        monkeypatch.setattr(be, "STATE_PATH", fake_state)

        be.mark_installed("ublock-origin", "firefox")
        be.mark_installed("ublock-origin", "chrome")
        be.unmark_installed("ublock-origin", "firefox")
        assert "firefox" not in be.get_installed("ublock-origin")
        assert "chrome" in be.get_installed("ublock-origin")

    def test_unmark_last_removes_entry(self, tmp_path, monkeypatch):
        """Ao desmarcar o ultimo browser, remove o ext_id do state."""
        fake_state = tmp_path / "state.json"
        monkeypatch.setattr(be, "STATE_PATH", fake_state)

        be.mark_installed("ublock-origin", "firefox")
        be.unmark_installed("ublock-origin", "firefox")
        assert be.get_installed("ublock-origin") == []

    def test_state_persists_on_disk(self, tmp_path, monkeypatch):
        fake_state = tmp_path / "state.json"
        monkeypatch.setattr(be, "STATE_PATH", fake_state)

        be.mark_installed("ublock-origin", "firefox")
        # Le do disco
        data = json.loads(fake_state.read_text())
        assert "ublock-origin" in data["installed"]
        assert "firefox" in data["installed"]["ublock-origin"]

    def test_double_mark_idempotent(self, tmp_path, monkeypatch):
        """Marcar 2x nao duplica."""
        fake_state = tmp_path / "state.json"
        monkeypatch.setattr(be, "STATE_PATH", fake_state)

        be.mark_installed("ublock-origin", "firefox")
        be.mark_installed("ublock-origin", "firefox")
        assert be.get_installed("ublock-origin").count("firefox") == 1


class TestConflicts:
    def test_no_conflict_when_alone(self, tmp_path, monkeypatch):
        fake_state = tmp_path / "state.json"
        monkeypatch.setattr(be, "STATE_PATH", fake_state)
        assert be.find_conflicts("ublock-origin", "firefox") == []

    def test_no_conflict_in_non_exclusive_category(self, tmp_path, monkeypatch):
        """Privacy Badger (tracker-blocker) nao conflita com ClearURLs (url-cleaner)."""
        fake_state = tmp_path / "state.json"
        monkeypatch.setattr(be, "STATE_PATH", fake_state)

        be.mark_installed("privacy-badger", "firefox")
        # ClearURLs e' outra categoria — sem conflito
        assert be.find_conflicts("clearurls", "firefox") == []

    def test_conflict_two_ad_blockers_same_browser(self, tmp_path, monkeypatch):
        """uBlock e AdGuard sao ambos ad-blocker — conflito."""
        fake_state = tmp_path / "state.json"
        monkeypatch.setattr(be, "STATE_PATH", fake_state)

        be.mark_installed("ublock-origin", "firefox")
        conflicts = be.find_conflicts("adguard-adblocker", "firefox")
        assert "ublock-origin" in conflicts

    def test_no_conflict_different_browsers(self, tmp_path, monkeypatch):
        """uBlock no Firefox + AdGuard no Chrome — sem conflito (browsers separados)."""
        fake_state = tmp_path / "state.json"
        monkeypatch.setattr(be, "STATE_PATH", fake_state)

        be.mark_installed("ublock-origin", "firefox")
        conflicts = be.find_conflicts("adguard-adblocker", "chrome")
        assert conflicts == []

    def test_conflict_not_with_self(self, tmp_path, monkeypatch):
        """Marcar uBlock duas vezes nao conflita consigo mesmo."""
        fake_state = tmp_path / "state.json"
        monkeypatch.setattr(be, "STATE_PATH", fake_state)

        be.mark_installed("ublock-origin", "firefox")
        conflicts = be.find_conflicts("ublock-origin", "firefox")
        assert "ublock-origin" not in conflicts


class TestFindExtension:
    def test_existing(self):
        ext = be.find_extension("ublock-origin")
        assert ext is not None
        assert ext.name == "uBlock Origin"

    def test_missing(self):
        assert be.find_extension("nao-existe") is None
