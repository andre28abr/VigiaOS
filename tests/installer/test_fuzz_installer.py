"""Fuzz tests pros parsers JSON do Tool Installer (Etapa E — hardening)."""

from __future__ import annotations

from vigia_installer import backend, browser_extensions as bext

FUZZ_JSON = [
    "", "   ", "lixo {{{", "{", "null", "42", "3.14", '"str"', "true",
    "[]", "[1, 2, 3]", '[{"x": 1}, "y"]', "{}", '{"chave": "errada"}',
    '{"deployments": "nao-lista"}', '{"deployments": [1, "x", null]}',
    '{"installed": "nao-dict"}', '{"installed": {"ext": "nao-lista"}}',
    '{"installed": {"ext": ["chrome", "firefox"]}}',
]


class FakeCP:
    def __init__(self, stdout: str, returncode: int = 0):
        self.stdout = stdout
        self.returncode = returncode


class TestRpmOstreeStatusRawFuzz:
    def test_always_returns_dict(self, monkeypatch):
        monkeypatch.setattr(backend, "rpm_ostree_available", lambda: True)
        for payload in FUZZ_JSON:
            monkeypatch.setattr(
                backend.subprocess, "run",
                lambda *a, _p=payload, **k: FakeCP(_p),
            )
            out = backend.rpm_ostree_status_raw()
            assert isinstance(out, dict), f"payload quebrou: {payload!r}"


class TestPendingChangesFuzz:
    def test_never_crashes(self, monkeypatch):
        weird = [
            None, 42, "x", [], [1, 2], {},
            {"deployments": "x"}, {"deployments": [1, 2]},
            {"deployments": [{"booted": True, "requested-packages": 5}]},
            {"deployments": [{"staged": True, "requested-packages": "abc"}]},
            {"deployments": [None, {"booted": True}]},
        ]
        for w in weird:
            monkeypatch.setattr(backend, "rpm_ostree_status_raw", lambda _w=w: _w)
            res = backend.pending_changes()
            assert res is not None, f"quebrou com: {w!r}"
            assert isinstance(res.current_layered, list)


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
