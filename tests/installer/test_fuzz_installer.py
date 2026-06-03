"""Fuzz tests pros parsers JSON do Tool Installer (Etapa E — hardening)."""

from __future__ import annotations

from vigia_installer import browser_extensions as bext

FUZZ_JSON = [
    "", "   ", "lixo {{{", "{", "null", "42", "3.14", '"str"', "true",
    "[]", "[1, 2, 3]", '[{"x": 1}, "y"]', "{}", '{"chave": "errada"}',
    '{"installed": "nao-dict"}', '{"installed": {"ext": "nao-lista"}}',
    '{"installed": {"ext": ["chrome", "firefox"]}}',
]


class TestBrowserExtStateFuzz:
    def test_get_installed_always_list(self, tmp_path, monkeypatch):
        p = tmp_path / "be.json"
        monkeypatch.setattr(bext, "STATE_PATH", p)
        for payload in FUZZ_JSON:
            p.write_text(payload, encoding="utf-8")
            out = bext.get_installed("alguma-ext")
            assert isinstance(out, list), f"payload quebrou: {payload!r}"

    def test_valid_marks_parse(self, tmp_path, monkeypatch):
        p = tmp_path / "be.json"
        monkeypatch.setattr(bext, "STATE_PATH", p)
        p.write_text('{"installed": {"ublock": ["firefox", "chrome"]}}', encoding="utf-8")
        assert bext.get_installed("ublock") == ["firefox", "chrome"]
        assert bext.get_installed("inexistente") == []

    def test_missing_file_ok(self, tmp_path, monkeypatch):
        monkeypatch.setattr(bext, "STATE_PATH", tmp_path / "naoexiste.json")
        assert bext.get_installed("x") == []
