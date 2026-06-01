"""Testes da identidade do escritório (config.py) + branding no render."""

from __future__ import annotations

import base64
from datetime import datetime

from vigia_reports import backend, config, renderer


class TestLoadSave:
    def test_defaults_when_absent(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "nope.json")
        assert config.load_config() == {
            "org_name": "", "org_subtitle": "", "responsible": "", "logo_path": ""
        }

    def test_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "CONFIG_DIR", tmp_path)
        monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "reports.json")
        config.save_config({
            "org_name": "SentinelBR", "org_subtitle": "OAB", "responsible": "André",
            "logo_path": "/x.png",
        })
        cfg = config.load_config()
        assert cfg["org_name"] == "SentinelBR"
        assert cfg["responsible"] == "André"
        assert cfg["logo_path"] == "/x.png"

    def test_save_strips_unknown_keys(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "CONFIG_DIR", tmp_path)
        monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "reports.json")
        config.save_config({"org_name": "X", "lixo": "y"})
        cfg = config.load_config()
        assert cfg["org_name"] == "X"
        assert "lixo" not in cfg


class TestLogoDataUri:
    def test_valid_png_roundtrips(self, tmp_path):
        p = tmp_path / "logo.png"
        p.write_bytes(b"\x89PNG\r\n fake-bytes")
        uri = config.logo_data_uri(str(p))
        assert uri.startswith("data:image/png;base64,")
        assert base64.b64decode(uri.split(",", 1)[1]) == b"\x89PNG\r\n fake-bytes"

    def test_empty_path(self):
        assert config.logo_data_uri("") == ""

    def test_unsupported_extension(self, tmp_path):
        p = tmp_path / "logo.txt"
        p.write_bytes(b"x")
        assert config.logo_data_uri(str(p)) == ""

    def test_missing_file(self, tmp_path):
        assert config.logo_data_uri(str(tmp_path / "nope.png")) == ""

    def test_oversized_rejected(self, tmp_path):
        p = tmp_path / "big.png"
        p.write_bytes(b"\x00" * (513 * 1024))
        assert config.logo_data_uri(str(p)) == ""


def _min_data():
    return {
        "period": backend.Period(since=datetime(2026, 5, 24), until=datetime(2026, 5, 31)),
        "elevated_mode": True,
        "status": {"level": "ok", "label": "x"},
        "summary": "s",
        "score": {"ok": 1, "total": 1, "pct": 100, "unknown": 0},
        "checks": [],
    }


class TestBrandingInRender:
    def test_org_in_header_and_footer(self, monkeypatch):
        monkeypatch.setattr(config, "org_context", lambda: {
            "name": "SentinelBR", "subtitle": "OAB/SP",
            "responsible": "André A. de Souza",
            "logo_uri": "data:image/png;base64,AAAA",
        })
        html = renderer.render_html("lgpd_compliance", _min_data())
        assert "SentinelBR" in html
        assert "OAB/SP" in html
        assert "André A. de Souza" in html
        assert "data:image/png;base64,AAAA" in html  # logo embutido

    def test_default_brand_when_empty(self, monkeypatch):
        monkeypatch.setattr(config, "org_context", lambda: {
            "name": "", "subtitle": "", "responsible": "", "logo_uri": "",
        })
        html = renderer.render_html("lgpd_compliance", _min_data())
        assert "VIGIA" in html  # fallback padrão
