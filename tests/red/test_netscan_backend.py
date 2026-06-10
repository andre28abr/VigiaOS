"""Testes do backend do Vigia Network Scanner (nmap). Puro: sem nmap, sem GTK."""

from __future__ import annotations

import pytest

from vigia_red.modules.netscan import backend as b

SAMPLE_XML = """<?xml version="1.0"?>
<nmaprun scanner="nmap">
  <host>
    <status state="up"/>
    <address addr="45.33.32.156" addrtype="ipv4"/>
    <hostnames><hostname name="scanme.nmap.org"/></hostnames>
    <ports>
      <port protocol="tcp" portid="80"><state state="open"/>
        <service name="http" product="Apache httpd"/></port>
      <port protocol="tcp" portid="22"><state state="open"/>
        <service name="ssh" product="OpenSSH" version="6.6.1p1"/></port>
      <port protocol="tcp" portid="443"><state state="closed"/>
        <service name="https"/></port>
    </ports>
  </host>
</nmaprun>"""


class TestValidateTarget:
    @pytest.mark.parametrize("t", [
        "exemplo.com", "exemplo.com.br", "scanme.nmap.org",
        "192.168.0.10", "10.0.0.1", "192.168.0.0/24", "2001:db8::1",
    ])
    def test_validos(self, t):
        assert b.validate_target(t)

    @pytest.mark.parametrize("t", ["", "   ", "http://", "exemplo .com", "a b"])
    def test_invalidos(self, t):
        assert not b.validate_target(t)

    def test_url_colada(self):
        assert b.validate_target("https://exemplo.com")


class TestNormalize:
    def test_tira_esquema(self):
        assert b.normalize_target("https://exemplo.com") == "exemplo.com"

    def test_mantem_cidr(self):
        assert b.normalize_target("192.168.0.0/24") == "192.168.0.0/24"


class TestNetworkTooLarge:
    def test_cidr_pequeno_ok(self):
        assert not b.network_too_large("192.168.0.0/24")   # 256

    def test_cidr_grande(self):
        assert b.network_too_large("10.0.0.0/16")          # 65536

    def test_limite_exato(self):
        assert not b.network_too_large("10.0.0.0/22")      # 1024 == MAX_HOSTS

    def test_dominio_e_ip_unico(self):
        assert not b.network_too_large("exemplo.com")
        assert not b.network_too_large("192.168.0.10")


class TestBuildCmd:
    def test_estrutura(self):
        cmd = b.build_scan_cmd("exemplo.com", ("-sV",))
        assert cmd[0] == "nmap"
        assert "-sT" in cmd and "-Pn" in cmd and "--open" in cmd
        assert "-sV" in cmd
        assert cmd[cmd.index("-oX") + 1] == "-"
        assert cmd[-1] == "exemplo.com"

    def test_sem_shell(self):
        cmd = b.build_scan_cmd("x.com", ("-F",))
        assert isinstance(cmd, list)
        joined = " ".join(cmd)
        assert ";" not in joined and "&&" not in joined and "|" not in joined


class TestParseXml:
    def test_extrai_host_e_portas(self):
        hosts = b.parse_nmap_xml(SAMPLE_XML)
        assert len(hosts) == 1
        h = hosts[0]
        assert h.address == "45.33.32.156"
        assert h.hostname == "scanme.nmap.org"
        # 443 está "closed" → fora; sobram 22 e 80, ordenados por porta
        assert [p.port for p in h.ports] == [22, 80]

    def test_servico_versao(self):
        h = b.parse_nmap_xml(SAMPLE_XML)[0]
        ssh = next(p for p in h.ports if p.port == 22)
        assert ssh.service == "ssh"
        assert ssh.describe() == "OpenSSH 6.6.1p1"
        http = next(p for p in h.ports if p.port == 80)
        assert http.describe() == "Apache httpd"

    def test_open_ports_property(self):
        r = b.ScanResult("x", hosts=b.parse_nmap_xml(SAMPLE_XML))
        assert r.open_ports == 2

    def test_lixo_nao_quebra(self):
        assert b.parse_nmap_xml("não é xml") == []
        assert b.parse_nmap_xml("") == []
        assert b.parse_nmap_xml("<nmaprun></nmaprun>") == []


class TestRegistry:
    def test_netscan_pronto(self):
        from vigia_red import registry
        m = next(m for m in registry.MODULES if m.id == "netscan")
        assert m.status == "pronto"
        assert m.impl == "vigia_red.modules.netscan.page"
        assert m.requires and "nmap" in m.requires[0].checks


class TestProfiles:
    def test_default_existe(self):
        ids = {p.id for p in b.PROFILES}
        assert b.DEFAULT_PROFILE in ids

    def test_describe_vazio(self):
        assert b.Port(22, service="ssh").describe() == "ssh"
        assert b.Port(22).describe() == ""
