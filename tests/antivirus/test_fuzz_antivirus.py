"""Fuzz tests pro parser JSON do Antivirus (Etapa E — hardening)."""

from __future__ import annotations

from vigia_antivirus import backend

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
        # reports validos sao dict (e ganham _file); os malucos sao pulados
        assert all(isinstance(d, dict) for d in out)

    def test_valid_report_parsed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(backend, "REPORTS_DIR", tmp_path)
        (tmp_path / "scan-ok.json").write_text(
            '{"target": "/home", "infected_files": 0}', encoding="utf-8"
        )
        out = backend.list_recent_reports()
        assert len(out) == 1
        assert out[0]["target"] == "/home"
        assert "_file" in out[0]
