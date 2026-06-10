"""Testes do backend do Vigia Recon (OSINT) + termo de uso do VigiaRed.

Tudo PURO — sem theHarvester instalado, sem rede, sem GTK.
"""

from __future__ import annotations

import pytest

from vigia_red import consent
from vigia_red.modules.recon import backend as b


class TestValidateDomain:
    @pytest.mark.parametrize("d", [
        "exemplo.com", "exemplo.com.br", "sub.exemplo.com.br",
        "a.co", "x-y.example.org", "MAIuscula.COM",
    ])
    def test_validos(self, d):
        assert b.validate_domain(d)

    @pytest.mark.parametrize("d", [
        "", "   ", "localhost", "semponto", "http://", "-x.com", "x-.com",
        "exemplo .com", "a..b.com",
    ])
    def test_invalidos(self, d):
        assert not b.validate_domain(d)

    def test_aceita_url_colada(self):
        assert b.validate_domain("https://sub.exemplo.com/path?x=1")


class TestNormalizeDomain:
    def test_remove_esquema_caminho_porta(self):
        assert b.normalize_domain("https://sub.exemplo.com:443/a/b") == "sub.exemplo.com"

    def test_remove_email_user(self):
        assert b.normalize_domain("user@exemplo.com") == "exemplo.com"

    def test_lower_e_trim(self):
        assert b.normalize_domain("  Exemplo.COM.  ") == "exemplo.com"

    def test_strip_www(self):
        assert b.normalize_domain("www.nmap.com") == "nmap.com"
        assert b.normalize_domain("https://www.exemplo.com.br/x") == "exemplo.com.br"

    def test_nao_strip_www_se_ficar_invalido(self):
        assert b.normalize_domain("www.com") == "www.com"  # 1 ponto: não vira "com"


class TestBuildCmd:
    def test_argv_estrutura(self):
        cmd = b.build_harvester_cmd("exemplo.com", ["crtsh", "otx"], "/tmp/out", 300)
        assert cmd[cmd.index("-d") + 1] == "exemplo.com"
        assert cmd[cmd.index("-b") + 1] == "crtsh,otx"
        assert cmd[cmd.index("-l") + 1] == "300"
        assert cmd[cmd.index("-f") + 1] == "/tmp/out"

    def test_e_lista_sem_shell(self):
        cmd = b.build_harvester_cmd("x.com", ["crtsh"], "/tmp/o")
        assert isinstance(cmd, list)
        assert all(isinstance(p, str) for p in cmd)
        joined = " ".join(cmd)
        assert ";" not in joined and "&&" not in joined and "|" not in joined

    def test_sem_fontes_usa_crtsh(self):
        cmd = b.build_harvester_cmd("x.com", [], "/tmp/o")
        assert cmd[cmd.index("-b") + 1] == "crtsh"


class TestParse:
    def test_extrai_tudo(self):
        data = {
            "emails": ["a@x.com"],
            "hosts": ["mail.x.com:1.2.3.4", "vpn.x.com"],
            "ips": ["9.9.9.9"],
            "interesting_urls": ["http://x.com/admin"],
        }
        r = b.parse_harvester_json(data, "x.com")
        assert r.emails == ["a@x.com"]
        assert "mail.x.com" in r.hosts and "vpn.x.com" in r.hosts
        assert "1.2.3.4" in r.ips and "9.9.9.9" in r.ips
        assert r.urls == ["http://x.com/admin"]
        assert r.total == 6  # 1 email + 2 hosts + 2 ips + 1 url

    def test_dedup_case_insensitive(self):
        r = b.parse_harvester_json({"emails": ["A@X.com", "a@x.com"]})
        assert r.emails == ["A@X.com"]

    def test_urls_key_alternativa(self):
        r = b.parse_harvester_json({"urls": ["http://x"]})
        assert r.urls == ["http://x"]

    def test_lixo_nao_quebra(self):
        assert b.parse_harvester_json(None).total == 0
        assert b.parse_harvester_json([]).total == 0
        assert b.parse_harvester_json({"hosts": [1, 2, None]}).total == 0

    def test_total_property(self):
        r = b.ReconResult("x.com", emails=["a"], hosts=["b", "c"])
        assert r.total == 3


class TestClean:
    def test_ordena_e_dedup(self):
        assert b._clean(["b", "A", "a", "", "b"]) == ["A", "b"]

    def test_ignora_nao_string(self):
        assert b._clean([1, None, "x"]) == ["x"]


class TestShortError:
    def test_ignora_banner_pega_linha_util(self):
        out = "*****\n* theHarvester 4.11 *\n*****\nERRO: rede indisponível"
        assert b._short_error(out, "") == "ERRO: rede indisponível"

    def test_prefere_stderr(self):
        assert b._short_error("saida", "falha X") == "falha X"

    def test_vazio_ou_so_banner(self):
        assert b._short_error("", "") == ""
        assert b._short_error("****\n|||", "") == ""


class TestUnsupportedEngines:
    def test_extrai_uma(self):
        t = "are not supported: {'threatminer'}\n[!] Invalid source."
        assert b._unsupported_engines(t) == {"threatminer"}

    def test_multiplas(self):
        assert b._unsupported_engines("not supported: {'a', 'b'}") == {"a", "b"}

    def test_nenhuma(self):
        assert b._unsupported_engines("tudo certo") == set()
        assert b._unsupported_engines("") == set()


class TestSources:
    def test_default_sao_ids_validos(self):
        ids = {s.id for s in b.SOURCES}
        assert set(b.DEFAULT_SOURCE_IDS).issubset(ids)


class TestRegistry:
    def test_recon_marcado_pronto(self):
        from vigia_red import registry
        recon = next(m for m in registry.MODULES if m.id == "recon")
        assert recon.status == "pronto"
        assert recon.impl == "vigia_red.modules.recon.page"
        assert recon.requires and recon.requires[0].checks


class TestConsent:
    def test_fresh_nao_aceito(self, tmp_path, monkeypatch):
        monkeypatch.setattr(consent, "CONSENT_FILE", tmp_path / "c.json")
        assert consent.is_accepted() is False

    def test_accept_persiste(self, tmp_path, monkeypatch):
        monkeypatch.setattr(consent, "CONSENT_FILE", tmp_path / "c.json")
        assert consent.accept()
        assert consent.is_accepted() is True

    def test_revoke(self, tmp_path, monkeypatch):
        monkeypatch.setattr(consent, "CONSENT_FILE", tmp_path / "c.json")
        consent.accept()
        consent.revoke()
        assert consent.is_accepted() is False
