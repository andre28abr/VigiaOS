"""Fuzz tests pros parsers JSON do Rootkit Scanner (Etapa E — hardening)."""

from __future__ import annotations

from vigia_rootkit import backend

FUZZ_JSON = [
    "", "   ", "lixo {{{", "{", "null", "42", "3.14", '"str"', "true",
    "[]", "[1, 2, 3]", '[{"x": 1}, "y", null]', "{}", '{"chave": "errada"}',
]


class TestListRecentReportsFuzz:
    def test_never_crashes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(backend, "REPORTS_DIR", tmp_path)
        for i, payload in enumerate(FUZZ_JSON):
            (tmp_path / f"scan-{i:03d}.json").write_text(payload, encoding="utf-8")
        out = backend.list_recent_reports()
        assert isinstance(out, list)
        assert all(isinstance(d, dict) for d in out)


class TestLoadReportFuzz:
    def test_returns_dict_or_none(self, tmp_path):
        for i, payload in enumerate(FUZZ_JSON):
            p = tmp_path / f"r-{i:03d}.json"
            p.write_text(payload, encoding="utf-8")
            res = backend.load_report(str(p))
            assert res is None or isinstance(res, dict), f"quebrou com: {payload!r}"

    def test_valid_report(self, tmp_path):
        p = tmp_path / "ok.json"
        p.write_text('{"scanner": "rkhunter", "infected_count": 0}', encoding="utf-8")
        res = backend.load_report(str(p))
        assert isinstance(res, dict)
        assert res["scanner"] == "rkhunter"

    def test_nonexistent_path(self):
        assert backend.load_report("/caminho/que/nao/existe.json") is None
