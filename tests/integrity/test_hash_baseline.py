"""Testes do hash_backend: deteccao de 'movido' + selecao de engine (hashdeep).

Tudo pure-Python (sem GTK) e sem precisar do hashdeep instalado — a
chamada ao hashdeep e' mockada via subprocess.run.
"""

from __future__ import annotations

import types

import pytest

from vigia_integrity import hash_backend as hb


@pytest.fixture(autouse=True)
def _isolate_baseline_dir(tmp_path, monkeypatch):
    """Aponta BASELINE_DIR pra um tmp — nenhum teste escreve baseline no
    ~/.local/share/vigia-hash/ real do usuario."""
    monkeypatch.setattr(hb, "BASELINE_DIR", tmp_path / "vigia-hash")


class TestDetectMoves:
    def test_pure_move(self):
        moved, rem, add = hb._detect_moves(
            ["a.txt"], ["sub/b.txt"],
            {"a.txt": "H1"}, {"sub/b.txt": "H1"},
        )
        assert moved == ["a.txt → sub/b.txt"]
        assert rem == [] and add == []

    def test_no_move_when_hash_differs(self):
        moved, rem, add = hb._detect_moves(
            ["a.txt"], ["b.txt"],
            {"a.txt": "H1"}, {"b.txt": "H2"},
        )
        assert moved == []
        assert rem == ["a.txt"] and add == ["b.txt"]

    def test_partial_one_move_one_real_removal(self):
        # 2 removidos com H1, 1 adicionado com H1 => 1 movido + 1 removido real
        moved, rem, add = hb._detect_moves(
            ["a.txt", "c.txt"], ["b.txt"],
            {"a.txt": "H1", "c.txt": "H1"}, {"b.txt": "H1"},
        )
        assert len(moved) == 1
        assert len(rem) == 1 and add == []

    def test_empty_inputs(self):
        moved, rem, add = hb._detect_moves([], [], {}, {})
        assert moved == [] and rem == [] and add == []


class TestBaselineMovedIntegration:
    # Hasheia um subdir `data/` (o baseline vai pra tmp/vigia-hash, irmao —
    # nunca dentro da pasta escaneada, senao apareceria como 'adicionado').
    def test_move_detected_end_to_end(self, tmp_path):
        data = tmp_path / "data"
        data.mkdir()
        (data / "a.txt").write_text("conteudo unico xyz")
        (data / "keep.txt").write_text("igual")
        r = hb.create_baseline_blocking(str(data))
        assert r.error == "" and r.engine == "python"

        (data / "sub").mkdir()
        (data / "a.txt").rename(data / "sub" / "b.txt")

        c = hb.compare_baseline_blocking(r.output_file, str(data))
        assert c.moved == ["a.txt → sub/b.txt"]
        assert c.added == [] and c.removed == [] and c.unchanged == 1

    def test_add_remove_modify_still_work(self, tmp_path):
        data = tmp_path / "data"
        data.mkdir()
        (data / "keep.txt").write_text("estavel")
        (data / "gone.txt").write_text("vai sumir")
        (data / "mod.txt").write_text("antes")
        r = hb.create_baseline_blocking(str(data))

        (data / "gone.txt").unlink()
        (data / "mod.txt").write_text("DEPOIS diferente")
        (data / "novo.txt").write_text("novinho")

        c = hb.compare_baseline_blocking(r.output_file, str(data))
        assert c.added == ["novo.txt"]
        assert c.removed == ["gone.txt"]
        assert c.modified == ["mod.txt"]
        assert c.moved == []
        assert c.unchanged == 1  # keep.txt


class TestEngineSelection:
    def test_python_when_not_requested(self, tmp_path, monkeypatch):
        monkeypatch.setattr(hb, "hashdeep_installed", lambda: True)
        (tmp_path / "x").write_text("x")
        _, engine = hb._hash_dir(str(tmp_path), "sha256", use_hashdeep=False)
        assert engine == "python"

    def test_fallback_when_hashdeep_absent(self, tmp_path, monkeypatch):
        monkeypatch.setattr(hb, "hashdeep_installed", lambda: False)
        (tmp_path / "x").write_text("x")
        _, engine = hb._hash_dir(str(tmp_path), "sha256", use_hashdeep=True)
        assert engine == "python"

    def test_sha512_forces_python(self, tmp_path, monkeypatch):
        # hashdeep nao suporta sha512 => cai pro python mesmo com toggle on
        monkeypatch.setattr(hb, "hashdeep_installed", lambda: True)
        (tmp_path / "x").write_text("x")
        _, engine = hb._hash_dir(str(tmp_path), "sha512", use_hashdeep=True)
        assert engine == "python"

    def test_hashdeep_used_and_parsed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(hb, "hashdeep_installed", lambda: True)
        fake_out = (
            "%%%% HASHDEEP-1.0\n"
            "%%%% size,sha256,filename\n"
            "## Invoked from: /tmp\n"
            "## $ hashdeep -r -c sha256 .\n"
            "11,abc123,./file1.txt\n"
            "22,def456,sub/file2.txt\n"
        )

        def fake_run(cmd, **kw):
            assert cmd[:3] == ["hashdeep", "-r", "-c"]
            return types.SimpleNamespace(returncode=0, stdout=fake_out, stderr="")

        monkeypatch.setattr(hb.subprocess, "run", fake_run)
        hashes, engine = hb._hash_dir(str(tmp_path), "sha256", use_hashdeep=True)
        assert engine == "hashdeep"
        assert hashes == {"file1.txt": "abc123", "sub/file2.txt": "def456"}

    def test_hashdeep_nonzero_falls_back(self, tmp_path, monkeypatch):
        monkeypatch.setattr(hb, "hashdeep_installed", lambda: True)
        (tmp_path / "x").write_text("x")

        def fake_run(cmd, **kw):
            return types.SimpleNamespace(returncode=1, stdout="", stderr="boom")

        monkeypatch.setattr(hb.subprocess, "run", fake_run)
        _, engine = hb._hash_dir(str(tmp_path), "sha256", use_hashdeep=True)
        assert engine == "python"  # returncode!=0 => None => fallback

    def test_hashdeep_filename_with_comma(self, monkeypatch, tmp_path):
        monkeypatch.setattr(hb, "hashdeep_installed", lambda: True)
        fake_out = "11,abc123,./a,b.txt\n"  # filename com virgula

        def fake_run(cmd, **kw):
            return types.SimpleNamespace(returncode=0, stdout=fake_out, stderr="")

        monkeypatch.setattr(hb.subprocess, "run", fake_run)
        hashes, _ = hb._hash_dir(str(tmp_path), "sha256", use_hashdeep=True)
        assert hashes == {"a,b.txt": "abc123"}
