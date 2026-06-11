"""Testes do backend do Vigia Web Scanner (wapiti). Puro: sem wapiti, sem GTK."""

from __future__ import annotations

import pytest

from vigia_red.modules.web import backend as b

SAMPLE = {
    "vulnerabilities": {
        "Cross Site Scripting": [
            {"method": "GET", "path": "/search", "info": "XSS no parâmetro q",
             "level": 3, "parameter": "q"},
        ],
        "SQL Injection": [
            {"method": "POST", "path": "/login", "info": "SQLi no login",
             "level": 3, "parameter": "user"},
        ],
        "Backup file": [
            {"method": "GET", "path": "/index.php.bak", "info": "Backup exposto",
             "level": 1, "parameter": ""},
        ],
    },
    "anomalies": {},
    "infos": {"target": "http://x", "version": "3.x"},
}


class TestValidate:
    @pytest.mark.parametrize("t", [
        "https://exemplo.com", "http://x.com/a?q=1", "exemplo.com.br",
        "192.168.0.1",
    ])
    def test_validos(self, t):
        assert b.validate_target(t)

    @pytest.mark.parametrize("t", ["", "   ", "a b"])
    def test_invalidos(self, t):
        assert not b.validate_target(t)

    def test_normaliza_prefixo(self):
        assert b.normalize_target("exemplo.com") == "http://exemplo.com"
        assert b.normalize_target("https://x.com") == "https://x.com"


class TestBuildCmd:
    def test_estrutura(self):
        cmd = b.build_scan_cmd("http://x.com", ("--scope", "folder"), "/tmp/r.json")
        assert cmd[0] == "wapiti"
        assert cmd[cmd.index("-u") + 1] == "http://x.com"
        assert cmd[cmd.index("-f") + 1] == "json"
        assert cmd[cmd.index("-o") + 1] == "/tmp/r.json"
        assert cmd[cmd.index("--scope") + 1] == "folder"

    def test_sem_shell(self):
        cmd = b.build_scan_cmd("http://x", (), "/tmp/r")
        assert all(isinstance(p, str) for p in cmd)
        assert ";" not in " ".join(cmd) and "&&" not in " ".join(cmd)


class TestParse:
    def test_ordena_por_severidade(self):
        fs = b.parse_wapiti_json(SAMPLE)
        assert [f.severity for f in fs] == ["high", "high", "low"]

    def test_campos(self):
        fs = b.parse_wapiti_json(SAMPLE)
        xss = next(f for f in fs if "Scripting" in f.category)
        assert xss.severity == "high"
        assert xss.path == "/search" and xss.parameter == "q"
        assert xss.method == "GET"

    def test_lixo_nao_quebra(self):
        assert b.parse_wapiti_json(None) == []
        assert b.parse_wapiti_json({}) == []
        assert b.parse_wapiti_json({"vulnerabilities": "x"}) == []

    def test_counts(self):
        c = b.counts_by_severity(b.parse_wapiti_json(SAMPLE))
        assert c == {"high": 2, "low": 1}

    def test_sev_default_medium(self):
        # achado sem "level" -> medium (web vuln costuma ser notável)
        fs = b.parse_wapiti_json({"vulnerabilities": {"X": [{"path": "/"}]}})
        assert fs[0].severity == "medium"


class TestExport:
    def test_txt(self):
        r = b.ScanResult("http://x.com", profile="padrao",
                         findings=b.parse_wapiti_json(SAMPLE))
        txt = b.result_to_text(r)
        assert "http://x.com" in txt and "Cross Site Scripting" in txt
        assert "HIGH" in txt


class TestRegistry:
    def test_web_pronto(self):
        from vigia_red import registry
        m = next(m for m in registry.MODULES if m.id == "web")
        assert m.status == "pronto"
        assert m.impl == "vigia_red.modules.web.page"
        assert m.requires and "wapiti" in m.requires[0].checks


class TestProfiles:
    def test_default(self):
        assert b.DEFAULT_PROFILE in {p.id for p in b.PROFILES}
