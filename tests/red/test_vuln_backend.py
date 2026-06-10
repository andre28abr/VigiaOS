"""Testes do backend do Vigia Vuln Scanner (nuclei). Puro: sem nuclei, sem GTK."""

from __future__ import annotations

import pytest

from vigia_red.modules.vuln import backend as b

SAMPLE = (
    '{"template-id":"CVE-2021-1234","info":{"name":"Example RCE",'
    '"severity":"critical","tags":["cve","rce"],'
    '"description":"Remote code execution."},'
    '"host":"https://x.com","matched-at":"https://x.com/api"}\n'
    '{"template-id":"tech-detect","info":{"name":"Apache","severity":"info",'
    '"tags":["tech"]},"host":"https://x.com","matched-at":"https://x.com"}\n'
    'linha de log que deve ser ignorada\n'
    '{"template-id":"exp-1","info":{"name":"Git exposto","severity":"medium",'
    '"tags":["exposure"]},"matched-at":"https://x.com/.git/config"}'
)


class TestValidate:
    @pytest.mark.parametrize("t", [
        "https://exemplo.com", "http://x.com/a", "exemplo.com",
        "exemplo.com.br", "192.168.0.1",
    ])
    def test_validos(self, t):
        assert b.validate_target(t)

    @pytest.mark.parametrize("t", ["", "   ", "x", "a b", "ftp://x"])
    def test_invalidos(self, t):
        assert not b.validate_target(t)


class TestBuildCmd:
    def test_estrutura(self):
        cmd = b.build_nuclei_cmd("https://x.com", ("-tags", "cve"))
        assert cmd[0] == "nuclei"
        assert cmd[cmd.index("-target") + 1] == "https://x.com"
        assert "-jsonl" in cmd and "-silent" in cmd and "-tags" in cmd

    def test_sem_shell(self):
        cmd = b.build_nuclei_cmd("x.com", ())
        assert all(isinstance(p, str) for p in cmd)
        joined = " ".join(cmd)
        assert ";" not in joined and "&&" not in joined and "|" not in joined


class TestParse:
    def test_ordena_por_severidade(self):
        fs = b.parse_nuclei_jsonl(SAMPLE)
        assert [f.severity for f in fs] == ["critical", "medium", "info"]
        assert fs[0].name == "Example RCE"
        assert fs[0].template_id == "CVE-2021-1234"

    def test_campos(self):
        crit = b.parse_nuclei_jsonl(SAMPLE)[0]
        assert crit.matched_at == "https://x.com/api"
        assert "cve" in crit.tags
        assert crit.description.startswith("Remote")

    def test_ignora_lixo(self):
        assert b.parse_nuclei_jsonl("não é json\n") == []
        assert b.parse_nuclei_jsonl("") == []

    def test_counts(self):
        c = b.counts_by_severity(b.parse_nuclei_jsonl(SAMPLE))
        assert c == {"critical": 1, "medium": 1, "info": 1}


class TestExport:
    def test_txt(self):
        r = b.ScanResult("x.com", profile="cves",
                         findings=b.parse_nuclei_jsonl(SAMPLE))
        txt = b.result_to_text(r)
        assert "Example RCE" in txt and "CRITICAL" in txt and "x.com" in txt


class TestRegistry:
    def test_vuln_pronto(self):
        from vigia_red import registry
        m = next(m for m in registry.MODULES if m.id == "vuln")
        assert m.status == "pronto"
        assert m.impl == "vigia_red.modules.vuln.page"
        assert m.requires and "nuclei" in m.requires[0].checks


class TestProfiles:
    def test_default(self):
        assert b.DEFAULT_PROFILE in {p.id for p in b.PROFILES}
