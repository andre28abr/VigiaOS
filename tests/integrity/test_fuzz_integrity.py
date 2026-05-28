"""Fuzz tests pros parsers JSON do File Integrity (Etapa E — hardening)."""

from __future__ import annotations

from vigia_integrity import backend, hash_backend

FUZZ_JSON = [
    "", "   ", "lixo {{{", "{", "null", "42", "3.14", '"str"', "true",
    "[]", "[1, 2, 3]", '[{"x": 1}, "y", null]', "{}", '{"chave": "errada"}',
    '{"hashes": "nao-dict"}', '{"hashes": [1, 2]}',
    '{"hashes": {"a.txt": "deadbeef"}, "directory": 123, "algorithm": null}',
    '{"directory": ["lista"], "algorithm": 42}',
]


class TestLoadStateFuzz:
    def test_always_returns_dict(self, tmp_path, monkeypatch):
        p = tmp_path / "fi.json"
        monkeypatch.setattr(backend, "STATE_FILE", p)
        for payload in FUZZ_JSON:
            p.write_text(payload, encoding="utf-8")
            out = backend.load_state()
            assert isinstance(out, dict), f"payload quebrou: {payload!r}"


class TestListBaselinesFuzz:
    def test_never_crashes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(hash_backend, "BASELINE_DIR", tmp_path)
        for i, payload in enumerate(FUZZ_JSON):
            (tmp_path / f"baseline-{i:03d}.json").write_text(payload, encoding="utf-8")
        out = hash_backend.list_baselines()
        assert isinstance(out, list)
        # itens validos viram dict; os malucos sao descartados
        assert all(isinstance(d, dict) for d in out)


class TestCompareBaselineFuzz:
    def test_never_crashes(self, tmp_path, monkeypatch):
        scan_dir = tmp_path / "scan"
        scan_dir.mkdir()  # vazio -> comparacao rapida
        for i, payload in enumerate(FUZZ_JSON):
            bf = tmp_path / f"bl-{i:03d}.json"
            bf.write_text(payload, encoding="utf-8")
            res = hash_backend.compare_baseline_blocking(str(bf), directory=str(scan_dir))
            assert res is not None, f"quebrou com: {payload!r}"
