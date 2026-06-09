"""Testes do humanize do Network Monitor (puro — sem rede)."""

from __future__ import annotations

from vigia_netmon import humanize as h


def test_state_labels_ptbr():
    assert h.state_label("ESTAB") == "Conectado"
    assert h.state_label("LISTEN") == "Escutando"
    assert h.state_label("TIME-WAIT") == "Encerrando"
    assert h.state_label("UNCONN") == "Inativo"
    assert h.state_label("SYN-SENT") == "Conectando"
    # desconhecido cai num capitalize, sem crashar
    assert h.state_label("FOO") == "Foo"


def test_split_host_port_ipv4():
    assert h.split_host_port("192.168.0.5:443") == ("192.168.0.5", "443")


def test_split_host_port_ipv6():
    assert h.split_host_port("[::1]:53") == ("::1", "53")


def test_split_host_port_no_port():
    assert h.split_host_port("semporta") == ("semporta", "")
    assert h.split_host_port("") == ("", "")


def test_is_loopback():
    assert h.is_loopback("127.0.0.1:631") is True
    assert h.is_loopback("127.0.0.54:53") is True
    assert h.is_loopback("[::1]:53") is True
    assert h.is_loopback("142.250.0.1:443") is False


def test_is_internet_peer():
    assert h.is_internet_peer("142.250.79.14:443") is True
    assert h.is_internet_peer("127.0.0.1:631") is False
    assert h.is_internet_peer("0.0.0.0:*") is False
    assert h.is_internet_peer("[::1]:53") is False
    assert h.is_internet_peer("*:*") is False


def test_port_hint():
    assert h.port_hint("22") == "Acesso remoto (SSH)"
    assert h.port_hint("443") == "Web seguro (HTTPS)"
    assert h.port_hint("631") == "Impressão (CUPS)"
    assert h.port_hint("99999") == ""


def test_resolve_host_uses_cache(monkeypatch):
    # Não toca a rede: pré-carrega o cache e confirma que devolve o valor.
    h._DNS_CACHE["203.0.113.7"] = "exemplo.com"
    assert h.resolve_host("203.0.113.7") == "exemplo.com"
    assert h.resolve_host("") == ""
