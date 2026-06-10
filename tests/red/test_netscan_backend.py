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
    <os><osmatch name="Linux 5.X" accuracy="95"/></os>
    <ports>
      <port protocol="tcp" portid="80"><state state="open"/>
        <service name="http" product="Apache httpd"/>
        <script id="http-title" output="Go ahead and ScanMe!"/></port>
      <port protocol="tcp" portid="22"><state state="open"/>
        <service name="ssh" product="OpenSSH" version="6.6.1p1"/></port>
      <port protocol="tcp" portid="443"><state state="closed"/></port>
    </ports>
  </host>
</nmaprun>"""


def _profile(pid):
    return next(p for p in b.PROFILES if p.id == pid)


class TestValidateTarget:
    @pytest.mark.parametrize("t", [
        "exemplo.com", "scanme.nmap.org", "192.168.0.10", "192.168.0.0/24",
        "2001:db8::1",
    ])
    def test_validos(self, t):
        assert b.validate_target(t)

    @pytest.mark.parametrize("t", ["", "   ", "http://", "exemplo .com", "a b"])
    def test_invalidos(self, t):
        assert not b.validate_target(t)


class TestNetworkTooLarge:
    def test_pequeno(self):
        assert not b.network_too_large("192.168.0.0/24")    # 256

    def test_grande(self):
        assert b.network_too_large("10.0.0.0/16")           # 65536

    def test_limite(self):
        assert not b.network_too_large("10.0.0.0/22")       # 1024


class TestValidatePorts:
    @pytest.mark.parametrize("p", ["", "80", "80,443", "8000-8100", "22,80,8000-8010"])
    def test_validos(self, p):
        assert b.validate_ports(p)

    @pytest.mark.parametrize("p", ["abc", "80,", "99999", "80-", "-80", "80 443"])
    def test_invalidos(self, p):
        assert not b.validate_ports(p)


class TestBuildCmd:
    def test_padrao_sem_root(self):
        cmd = b.build_scan_cmd("exemplo.com", _profile("padrao"))
        assert cmd[0] == "nmap" and "pkexec" not in cmd
        assert "-sT" in cmd and "-sV" in cmd
        assert cmd[cmd.index("-oX") + 1] == "-"
        assert cmd[-1] == "exemplo.com"

    def test_elevated_prefixa_pkexec(self):
        cmd = b.build_scan_cmd("x.com", _profile("furtiva"), elevated=True)
        assert cmd[0] == "pkexec" and cmd[1] == "nmap"
        assert "-sS" in cmd and "-sT" not in cmd

    def test_furtiva_sem_root_degrada(self):
        cmd = b.build_scan_cmd("x.com", _profile("furtiva"))
        assert "-sS" not in cmd and "-sT" in cmd

    def test_portas_custom_sobrescrevem(self):
        cmd = b.build_scan_cmd("x.com", _profile("padrao"), ports="80,443")
        assert cmd[cmd.index("-p") + 1] == "80,443"

    def test_scripts(self):
        cmd = b.build_scan_cmd("x.com", _profile("padrao"), scripts="vuln")
        assert cmd[cmd.index("--script") + 1] == "vuln"

    def test_ping_sweep(self):
        cmd = b.build_scan_cmd("192.168.0.0/24", _profile("pingsweep"))
        assert "-sn" in cmd and "--open" not in cmd and "-p" not in cmd
        assert cmd[-1] == "192.168.0.0/24"

    def test_sem_shell(self):
        cmd = b.build_scan_cmd("x.com", _profile("rapida"))
        assert all(isinstance(p, str) for p in cmd)
        joined = " ".join(cmd)
        assert ";" not in joined and "&&" not in joined and "|" not in joined


class TestParseXml:
    def test_host_portas_os(self):
        hosts = b.parse_nmap_xml(SAMPLE_XML)
        assert len(hosts) == 1
        h = hosts[0]
        assert h.address == "45.33.32.156"
        assert h.hostname == "scanme.nmap.org"
        assert h.os == "Linux 5.X"
        assert [p.port for p in h.ports] == [22, 80]   # 443 closed → fora

    def test_scripts_na_porta(self):
        h = b.parse_nmap_xml(SAMPLE_XML)[0]
        p80 = next(p for p in h.ports if p.port == 80)
        assert any("http-title" in s for s in p80.scripts)

    def test_servico_versao(self):
        h = b.parse_nmap_xml(SAMPLE_XML)[0]
        ssh = next(p for p in h.ports if p.port == 22)
        assert ssh.describe() == "OpenSSH 6.6.1p1"

    def test_open_ports(self):
        r = b.ScanResult("x", hosts=b.parse_nmap_xml(SAMPLE_XML))
        assert r.open_ports == 2

    def test_lixo(self):
        assert b.parse_nmap_xml("não é xml") == []
        assert b.parse_nmap_xml("") == []


class TestExportText:
    def test_txt(self):
        r = b.ScanResult("x.com", profile="padrao",
                         hosts=b.parse_nmap_xml(SAMPLE_XML))
        txt = b.result_to_text(r)
        assert "x.com" in txt and "22/tcp" in txt and "OpenSSH" in txt
        assert "Linux 5.X" in txt


class TestRegistry:
    def test_netscan_pronto(self):
        from vigia_red import registry
        m = next(m for m in registry.MODULES if m.id == "netscan")
        assert m.status == "pronto"
        assert m.impl == "vigia_red.modules.netscan.page"
        assert m.requires and "nmap" in m.requires[0].checks


class TestProfiles:
    def test_default_existe(self):
        assert b.DEFAULT_PROFILE in {p.id for p in b.PROFILES}

    def test_admin_flag(self):
        assert _profile("furtiva").needs_root
        assert not _profile("padrao").needs_root

    def test_describe_vazio(self):
        assert b.Port(22, service="ssh").describe() == "ssh"
        assert b.Port(22).describe() == ""
