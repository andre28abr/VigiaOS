"""Tests pro state local de labels + notas do Deployments Manager."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from vigia_deployments import state


# ============================================================
# Labels
# ============================================================


class TestLabels:
    def test_empty_state_returns_empty(self, tmp_path, monkeypatch):
        fake = tmp_path / "state.json"
        monkeypatch.setattr(state, "STATE_PATH", fake)
        assert state.get_label("anychecksum") == ""

    def test_set_get_label(self, tmp_path, monkeypatch):
        fake = tmp_path / "state.json"
        monkeypatch.setattr(state, "STATE_PATH", fake)

        ok = state.set_label("abc123", "Meu label custom")
        assert ok
        assert state.get_label("abc123") == "Meu label custom"

    def test_set_empty_label_removes(self, tmp_path, monkeypatch):
        fake = tmp_path / "state.json"
        monkeypatch.setattr(state, "STATE_PATH", fake)

        state.set_label("abc123", "Algum label")
        state.set_label("abc123", "")
        assert state.get_label("abc123") == ""

    def test_empty_checksum_rejected(self):
        assert state.set_label("", "label") is False
        assert state.get_label("") == ""

    def test_state_file_mode_0600(self, tmp_path, monkeypatch):
        fake = tmp_path / "state.json"
        monkeypatch.setattr(state, "STATE_PATH", fake)

        state.set_label("abc", "test")
        assert fake.exists()
        mode = fake.stat().st_mode & 0o777
        assert mode == 0o600, f"Esperava 0600, foi {oct(mode)}"

    def test_label_strip(self, tmp_path, monkeypatch):
        """Espaços em branco sao removidos."""
        fake = tmp_path / "state.json"
        monkeypatch.setattr(state, "STATE_PATH", fake)
        state.set_label("abc", "  meu label  ")
        assert state.get_label("abc") == "meu label"


# ============================================================
# Notes
# ============================================================


class TestNotes:
    def test_empty_returns_empty(self, tmp_path, monkeypatch):
        fake = tmp_path / "state.json"
        monkeypatch.setattr(state, "STATE_PATH", fake)
        assert state.get_notes("anything") == ""

    def test_set_get_notes(self, tmp_path, monkeypatch):
        fake = tmp_path / "state.json"
        monkeypatch.setattr(state, "STATE_PATH", fake)
        notes_text = "Linha 1\nLinha 2\nLinha 3"
        state.set_notes("abc", notes_text)
        assert state.get_notes("abc") == notes_text

    def test_notes_preserves_newlines(self, tmp_path, monkeypatch):
        fake = tmp_path / "state.json"
        monkeypatch.setattr(state, "STATE_PATH", fake)
        notes_text = "Linha 1\nLinha 2\n"
        state.set_notes("abc", notes_text)
        # JSON preserva \n
        assert "\n" in state.get_notes("abc")

    def test_set_empty_removes(self, tmp_path, monkeypatch):
        fake = tmp_path / "state.json"
        monkeypatch.setattr(state, "STATE_PATH", fake)
        state.set_notes("abc", "algo")
        state.set_notes("abc", "")
        assert state.get_notes("abc") == ""


# ============================================================
# Labels + notes juntos
# ============================================================


class TestCombined:
    def test_both_in_same_file(self, tmp_path, monkeypatch):
        fake = tmp_path / "state.json"
        monkeypatch.setattr(state, "STATE_PATH", fake)
        state.set_label("abc", "Meu label")
        state.set_notes("abc", "Nota 1\nNota 2")

        data = json.loads(fake.read_text())
        assert "labels" in data
        assert "notes" in data
        assert data["labels"]["abc"] == "Meu label"
        assert "Nota 1" in data["notes"]["abc"]

    def test_independent_checksums(self, tmp_path, monkeypatch):
        fake = tmp_path / "state.json"
        monkeypatch.setattr(state, "STATE_PATH", fake)
        state.set_label("aaa", "Label A")
        state.set_label("bbb", "Label B")
        assert state.get_label("aaa") == "Label A"
        assert state.get_label("bbb") == "Label B"


# ============================================================
# cleanup_orphaned
# ============================================================


class TestCleanupOrphaned:
    def test_removes_dead_checksums(self, tmp_path, monkeypatch):
        fake = tmp_path / "state.json"
        monkeypatch.setattr(state, "STATE_PATH", fake)
        state.set_label("alive1", "label A")
        state.set_label("alive2", "label B")
        state.set_label("dead", "label antigo")
        state.set_notes("dead", "notas antigas")

        # Soh "alive1" e "alive2" estao no rpm-ostree agora
        removed = state.cleanup_orphaned(["alive1", "alive2"])
        assert removed == 2  # 1 label morto + 1 notes morta
        assert state.get_label("alive1") == "label A"
        assert state.get_label("dead") == ""
        assert state.get_notes("dead") == ""

    def test_no_orphans_returns_zero(self, tmp_path, monkeypatch):
        fake = tmp_path / "state.json"
        monkeypatch.setattr(state, "STATE_PATH", fake)
        state.set_label("alive", "A")
        removed = state.cleanup_orphaned(["alive"])
        assert removed == 0

    def test_empty_state_safe(self, tmp_path, monkeypatch):
        fake = tmp_path / "state.json"
        monkeypatch.setattr(state, "STATE_PATH", fake)
        removed = state.cleanup_orphaned(["abc"])
        assert removed == 0


# ============================================================
# Persistence + atomic write
# ============================================================


class TestPersistence:
    def test_reload_after_set(self, tmp_path, monkeypatch):
        """Salva, recarrega — valor persiste."""
        fake = tmp_path / "state.json"
        monkeypatch.setattr(state, "STATE_PATH", fake)
        state.set_label("abc", "primeiro")
        # Force reload
        assert state.get_label("abc") == "primeiro"

    def test_directory_created(self, tmp_path, monkeypatch):
        """Cria parent dir se nao existir."""
        fake = tmp_path / "nested" / "deep" / "state.json"
        monkeypatch.setattr(state, "STATE_PATH", fake)
        state.set_label("abc", "test")
        assert fake.exists()
        assert fake.parent.exists()

    def test_corrupted_json_returns_empty(self, tmp_path, monkeypatch):
        """JSON malformado nao crasha — retorna estado vazio."""
        fake = tmp_path / "state.json"
        fake.write_text("not { valid json")
        monkeypatch.setattr(state, "STATE_PATH", fake)
        # Nao crasha
        assert state.get_label("anything") == ""
