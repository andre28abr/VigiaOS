"""Testes dos parsers e validacoes do backend do firewall-gui.

Cobre (vigia_firewall.backend), sem firewalld real:
- get_active_zones(): parser multi-linha de `firewall-cmd --get-active-zones`
  (zona -> linha `interfaces:` -> linha `sources:`).
- list_zone_ports(): parse de "8080/tcp 53/udp 8000-8010/tcp" -> PortRule.
- add_zone_port(): validacao anti-injection (protocolo / porta) via ValueError.
- PortRule.to_arg().

A unica chamada de subprocess que importa aqui e' o wrapper `_fw_cmd`
(retorna (rc, stdout, stderr)). Para o caminho de escrita (add_zone_port)
mockamos `_pkexec_fw` e `_reload` para nao tocar pkexec/firewalld.

O backend NAO importa gi/PyGObject, entao roda headless.
"""

from __future__ import annotations

import pytest

from vigia_firewall import backend


# ============================================================
# Helpers de monkeypatch
# ============================================================


def _fake_fw(rc: int, stdout: str = "", stderr: str = ""):
    """Fabrica um substituto de _fw_cmd que ignora os args e devolve fixo.

    Espelha o _fw_cmd real, que faz .strip() em stdout/stderr.
    """
    def _inner(*args, timeout: int = 10):
        return rc, stdout.strip(), stderr.strip()

    return _inner


# ============================================================
# get_active_zones
# ============================================================


class TestGetActiveZones:
    def test_two_zones_interfaces_and_sources(self, monkeypatch):
        # public tem interfaces; trusted tem sources. Cabecalho de zona
        # sem indentacao; sub-linhas indentadas (como o firewall-cmd emite).
        out = (
            "public\n"
            "  interfaces: eth0 wlan0\n"
            "  sources: \n"
            "trusted\n"
            "  interfaces: \n"
            "  sources: 10.0.0.0/24 192.168.1.0/24\n"
        )
        monkeypatch.setattr(backend, "_fw_cmd", _fake_fw(0, out))

        zones = backend.get_active_zones()
        assert len(zones) == 2

        public, trusted = zones
        assert public.name == "public"
        assert public.interfaces == ["eth0", "wlan0"]
        assert public.sources == []

        assert trusted.name == "trusted"
        assert trusted.interfaces == []
        assert trusted.sources == ["10.0.0.0/24", "192.168.1.0/24"]

    def test_zone_without_sublines(self, monkeypatch):
        # Zona declarada mas sem linhas interfaces:/sources: -> listas vazias.
        out = "docker\n"
        monkeypatch.setattr(backend, "_fw_cmd", _fake_fw(0, out))

        zones = backend.get_active_zones()
        assert len(zones) == 1
        assert zones[0].name == "docker"
        assert zones[0].interfaces == []
        assert zones[0].sources == []

    def test_empty_output_returns_empty_list(self, monkeypatch):
        monkeypatch.setattr(backend, "_fw_cmd", _fake_fw(0, ""))
        assert backend.get_active_zones() == []

    def test_nonzero_rc_returns_empty_list(self, monkeypatch):
        # Daemon parado / erro: rc != 0 -> [] (mesmo que stdout tenha lixo).
        monkeypatch.setattr(backend, "_fw_cmd", _fake_fw(1, "public\n  interfaces: eth0\n"))
        assert backend.get_active_zones() == []


# ============================================================
# list_zone_ports
# ============================================================


class TestListZonePorts:
    def test_parses_three_rules(self, monkeypatch):
        monkeypatch.setattr(
            backend, "_fw_cmd", _fake_fw(0, "8080/tcp 53/udp 8000-8010/tcp")
        )
        rules = backend.list_zone_ports("public")
        assert len(rules) == 3
        assert all(isinstance(r, backend.PortRule) for r in rules)

        assert rules[0].port == "8080"
        assert rules[0].protocol == "tcp"
        assert rules[1].port == "53"
        assert rules[1].protocol == "udp"
        assert rules[2].port == "8000-8010"
        assert rules[2].protocol == "tcp"

    def test_token_without_slash_is_skipped(self, monkeypatch):
        # "lixo" nao tem '/', deve ser ignorado; "443/tcp" entra.
        monkeypatch.setattr(backend, "_fw_cmd", _fake_fw(0, "lixo 443/tcp"))
        rules = backend.list_zone_ports("public")
        assert len(rules) == 1
        assert rules[0].to_arg() == "443/tcp"

    def test_empty_returns_empty(self, monkeypatch):
        monkeypatch.setattr(backend, "_fw_cmd", _fake_fw(0, ""))
        assert backend.list_zone_ports("public") == []

    def test_nonzero_rc_returns_empty(self, monkeypatch):
        monkeypatch.setattr(backend, "_fw_cmd", _fake_fw(1, "8080/tcp"))
        assert backend.list_zone_ports("public") == []


# ============================================================
# add_zone_port: validacao anti-injection
# ============================================================


class TestAddZonePortValidation:
    def test_invalid_protocol_raises(self, monkeypatch):
        # Mocka o caminho de escrita: se a validacao falhar e deixar passar,
        # estes mocks evitam tocar pkexec, mas o teste exige o ValueError.
        called = {"pkexec": False, "reload": False}
        monkeypatch.setattr(
            backend, "_pkexec_fw", lambda *a, **k: called.__setitem__("pkexec", True)
        )
        monkeypatch.setattr(
            backend, "_reload", lambda: called.__setitem__("reload", True)
        )

        with pytest.raises(ValueError):
            backend.add_zone_port("public", "8080", "icmp")

        # Nao pode ter chamado o caminho privilegiado.
        assert called["pkexec"] is False
        assert called["reload"] is False

    def test_non_numeric_port_raises(self, monkeypatch):
        called = {"pkexec": False}
        monkeypatch.setattr(
            backend, "_pkexec_fw", lambda *a, **k: called.__setitem__("pkexec", True)
        )
        monkeypatch.setattr(backend, "_reload", lambda: None)

        with pytest.raises(ValueError):
            backend.add_zone_port("public", "abc", "tcp")
        assert called["pkexec"] is False

    def test_injection_like_port_raises(self, monkeypatch):
        # Tentativa de injection no token de porta deve bater na validacao.
        monkeypatch.setattr(backend, "_pkexec_fw", lambda *a, **k: None)
        monkeypatch.setattr(backend, "_reload", lambda: None)
        with pytest.raises(ValueError):
            backend.add_zone_port("public", "80; rm -rf /", "tcp")

    def test_valid_range_is_accepted(self, monkeypatch):
        # "8000-8010"/tcp e' valido: deve passar pela validacao e chamar
        # _pkexec_fw com o arg correto, depois _reload. Sem pkexec/firewalld real.
        captured = {}
        monkeypatch.setattr(
            backend, "_pkexec_fw", lambda *a, **k: captured.__setitem__("args", a)
        )
        monkeypatch.setattr(
            backend, "_reload", lambda: captured.__setitem__("reloaded", True)
        )

        backend.add_zone_port("public", "8000-8010", "tcp")

        assert captured.get("reloaded") is True
        # O arg de porta foi montado como "8000-8010/tcp".
        assert "--add-port=8000-8010/tcp" in captured["args"]
        assert "--zone=public" in captured["args"]
        assert "--permanent" in captured["args"]

    def test_valid_single_port_is_accepted(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(
            backend, "_pkexec_fw", lambda *a, **k: captured.__setitem__("args", a)
        )
        monkeypatch.setattr(backend, "_reload", lambda: None)

        backend.add_zone_port("trusted", "8080", "udp")
        assert "--add-port=8080/udp" in captured["args"]


# ============================================================
# PortRule.to_arg
# ============================================================


class TestPortRuleToArg:
    def test_single_port(self):
        assert backend.PortRule("8080", "tcp").to_arg() == "8080/tcp"

    def test_range(self):
        assert backend.PortRule("8000-8010", "udp").to_arg() == "8000-8010/udp"
