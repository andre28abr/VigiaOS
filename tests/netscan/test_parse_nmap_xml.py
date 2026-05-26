"""Testes para vigia_netscan.backend._parse_nmap_xml.

Parse de XML do nmap. Output bem-formado e malformado. Robustez.
"""

from __future__ import annotations

import pytest

from vigia_netscan.backend import _parse_nmap_xml


SAMPLE_NMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<nmaprun scanner="nmap">
  <host>
    <status state="up" />
    <address addr="192.168.1.1" addrtype="ipv4" />
    <hostnames>
      <hostname name="router.local" />
    </hostnames>
    <ports>
      <port protocol="tcp" portid="22">
        <state state="open" />
        <service name="ssh" product="OpenSSH" version="9.0" />
      </port>
      <port protocol="tcp" portid="443">
        <state state="open" />
        <service name="https" product="nginx" version="1.24.0" />
      </port>
      <port protocol="tcp" portid="80">
        <state state="closed" />
      </port>
    </ports>
  </host>
  <host>
    <status state="down" />
    <address addr="192.168.1.2" addrtype="ipv4" />
  </host>
</nmaprun>
"""

EMPTY_NMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<nmaprun scanner="nmap">
</nmaprun>
"""

PING_SCAN_XML = """<?xml version="1.0" encoding="UTF-8"?>
<nmaprun scanner="nmap">
  <host>
    <status state="up" />
    <address addr="10.0.0.1" addrtype="ipv4" />
  </host>
</nmaprun>
"""


class TestBasicParsing:
    def test_count_hosts(self):
        hosts = _parse_nmap_xml(SAMPLE_NMAP_XML)
        assert len(hosts) == 2

    def test_host_addresses(self):
        hosts = _parse_nmap_xml(SAMPLE_NMAP_XML)
        addrs = [h.address for h in hosts]
        assert "192.168.1.1" in addrs
        assert "192.168.1.2" in addrs

    def test_host_status(self):
        hosts = _parse_nmap_xml(SAMPLE_NMAP_XML)
        up_hosts = [h for h in hosts if h.status == "up"]
        down_hosts = [h for h in hosts if h.status == "down"]
        assert len(up_hosts) == 1
        assert len(down_hosts) == 1

    def test_hostname_extracted(self):
        hosts = _parse_nmap_xml(SAMPLE_NMAP_XML)
        up_host = next(h for h in hosts if h.status == "up")
        assert up_host.hostname == "router.local"


class TestPortParsing:
    def test_port_count(self):
        hosts = _parse_nmap_xml(SAMPLE_NMAP_XML)
        up_host = next(h for h in hosts if h.status == "up")
        assert len(up_host.ports) == 3

    def test_port_22_ssh(self):
        hosts = _parse_nmap_xml(SAMPLE_NMAP_XML)
        up_host = next(h for h in hosts if h.status == "up")
        ssh = next(p for p in up_host.ports if p.port == 22)
        assert ssh.protocol == "tcp"
        assert ssh.state == "open"
        assert ssh.service == "ssh"
        assert ssh.product == "OpenSSH"
        assert ssh.version == "9.0"

    def test_port_443_https(self):
        hosts = _parse_nmap_xml(SAMPLE_NMAP_XML)
        up_host = next(h for h in hosts if h.status == "up")
        https = next(p for p in up_host.ports if p.port == 443)
        assert https.state == "open"
        assert https.product == "nginx"
        assert https.version == "1.24.0"

    def test_closed_port_preserved(self):
        hosts = _parse_nmap_xml(SAMPLE_NMAP_XML)
        up_host = next(h for h in hosts if h.status == "up")
        closed = next(p for p in up_host.ports if p.port == 80)
        assert closed.state == "closed"


class TestEdgeCases:
    def test_empty_xml(self):
        hosts = _parse_nmap_xml(EMPTY_NMAP_XML)
        assert hosts == []

    def test_ping_scan(self):
        """Ping scan (-sn) nao tem <ports>, so status."""
        hosts = _parse_nmap_xml(PING_SCAN_XML)
        assert len(hosts) == 1
        assert hosts[0].status == "up"
        assert hosts[0].ports == []

    def test_host_without_status(self):
        """Host sem <status> element nao deve quebrar."""
        xml = """<?xml version="1.0"?><nmaprun>
        <host>
          <address addr="1.1.1.1" addrtype="ipv4" />
        </host>
        </nmaprun>"""
        hosts = _parse_nmap_xml(xml)
        assert len(hosts) == 1
        assert hosts[0].address == "1.1.1.1"
        # status nao detectado — fica string vazia
        assert hosts[0].status == ""

    def test_malformed_xml_raises(self):
        """XML invalido deve lancar ParseError."""
        from xml.etree.ElementTree import ParseError
        with pytest.raises(ParseError):
            _parse_nmap_xml("<<not xml")

    def test_xml_without_addresses(self):
        xml = """<?xml version="1.0"?><nmaprun>
        <host>
          <status state="up" />
        </host>
        </nmaprun>"""
        hosts = _parse_nmap_xml(xml)
        assert len(hosts) == 1
        assert hosts[0].address == ""
        assert hosts[0].status == "up"
