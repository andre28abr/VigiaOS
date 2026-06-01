"""Testes do despachante de coleta + modo headless (cli.py)."""

from __future__ import annotations

import pytest

from vigia_reports import backend, cli


def _fake_lgpd(period, elevated=False):
    return {
        "period": period, "elevated_mode": True,
        "status": {"level": "ok", "label": "x"}, "summary": "s",
        "score": {"ok": 1, "total": 1, "pct": 100, "unknown": 0}, "checks": [],
    }


class TestCollectFor:
    def test_dispatches_to_collector(self, monkeypatch):
        seen = {}

        def fake(period, elevated=False):
            seen["args"] = (period, elevated)
            return {"ok": 1}

        monkeypatch.setitem(backend.COLLECTORS, "lgpd_compliance", fake)
        out = backend.collect_for("lgpd_compliance", backend.make_period(7), elevated=True)
        assert out == {"ok": 1}
        assert seen["args"][1] is True

    def test_unknown_model_raises(self):
        with pytest.raises(ValueError):
            backend.collect_for("nao_existe", backend.make_period(7))


class TestHeadlessGenerate:
    def test_generate_writes_html_and_sidecar(self, tmp_path, monkeypatch):
        monkeypatch.setattr(backend, "ensure_reports_dir", lambda: tmp_path)
        monkeypatch.setitem(backend.COLLECTORS, "lgpd_compliance", _fake_lgpd)
        path = cli.generate("lgpd_compliance", 7, False)
        assert path.exists() and path.suffix == ".html"
        assert path.with_name(path.name + ".sha256").exists()

    def test_main_headless_prints_path(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(backend, "ensure_reports_dir", lambda: tmp_path)
        monkeypatch.setitem(backend.COLLECTORS, "lgpd_compliance", _fake_lgpd)
        rc = cli.main_headless(["--generate", "lgpd_compliance", "--period", "7"])
        assert rc == 0
        assert capsys.readouterr().out.strip().endswith(".html")

    def test_invalid_model_exits(self):
        with pytest.raises(SystemExit):
            cli.main_headless(["--generate", "nao_existe"])
