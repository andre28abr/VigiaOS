"""Tests para o parser do output de `resolvectl status`.

Critico porque sem parser correto, a aba Status mostra dados errados
e a aba Provedores nao detecta "Em uso" corretamente.
"""

from __future__ import annotations

import pytest

from vigia_dns.backend import (
    InterfaceDns,
    ResolvedStatus,
    _parse_resolvectl_status,
)


# ============================================================
# Outputs reais de resolvectl status (capturados em sistemas
# Silverblue, Workstation, e VM)
# ============================================================


OUTPUT_SIMPLE = """\
Global
       Protocols: -LLMNR -mDNS +DNSOverTLS DNSSEC=no/unsupported
resolv.conf mode: stub
Current DNS Server: 1.1.1.1
       DNS Servers: 1.1.1.1 1.0.0.1
"""

OUTPUT_WITH_INTERFACE = """\
Global
       Protocols: -LLMNR -mDNS +DNSOverTLS DNSSEC=no/unsupported
resolv.conf mode: stub
Current DNS Server: 1.1.1.1
       DNS Servers: 1.1.1.1 1.0.0.1
       Fallback DNS Servers: 9.9.9.9

Link 2 (wlp2s0)
    Current Scopes: DNS
         Protocols: +DefaultRoute +LLMNR -mDNS -DNSOverTLS DNSSEC=no/unsupported
Current DNS Server: 192.168.1.1
       DNS Servers: 192.168.1.1
        DNS Domain: lan
"""

OUTPUT_MULTIPLE_INTERFACES = """\
Global
       Protocols: -LLMNR -mDNS +DNSOverTLS DNSSEC=no/unsupported

Link 2 (eth0)
    Current Scopes: DNS
         Protocols: +DefaultRoute -LLMNR -mDNS +DNSOverTLS
Current DNS Server: 192.168.1.1
       DNS Servers: 192.168.1.1 8.8.8.8

Link 3 (wlp2s0)
    Current Scopes: DNS
         Protocols: +DefaultRoute +LLMNR -mDNS -DNSOverTLS
Current DNS Server: 10.0.0.1
       DNS Servers: 10.0.0.1
        DNS Domain: corp.example.com
"""

OUTPUT_NO_DNS_CONFIGURED = """\
Global
       Protocols: -LLMNR -mDNS -DNSOverTLS
resolv.conf mode: stub
"""

OUTPUT_DOT_DISABLED = """\
Global
       Protocols: -LLMNR -mDNS -DNSOverTLS DNSSEC=no/unsupported
       DNS Servers: 8.8.8.8 8.8.4.4
"""


# ============================================================
# Tests
# ============================================================


class TestParseSimple:
    def test_basic_global_dns(self):
        st = ResolvedStatus()
        _parse_resolvectl_status(st, OUTPUT_SIMPLE)
        assert st.global_dns == ["1.1.1.1", "1.0.0.1"]
        assert st.current_dns == ["1.1.1.1"]
        assert st.global_dot == "yes"

    def test_no_interfaces_in_simple(self):
        st = ResolvedStatus()
        _parse_resolvectl_status(st, OUTPUT_SIMPLE)
        assert st.interfaces == []


class TestParseWithInterface:
    def test_global_and_interface_parsed(self):
        st = ResolvedStatus()
        _parse_resolvectl_status(st, OUTPUT_WITH_INTERFACE)
        # Global
        assert st.global_dns == ["1.1.1.1", "1.0.0.1"]
        assert st.global_dot == "yes"
        assert st.fallback_dns == ["9.9.9.9"]
        # Interface
        assert len(st.interfaces) == 1
        iface = st.interfaces[0]
        assert iface.name == "wlp2s0"
        assert iface.dns_servers == ["192.168.1.1"]
        assert iface.dns_over_tls == "no"
        assert iface.domains == ["lan"]

    def test_current_dns_captured(self):
        st = ResolvedStatus()
        _parse_resolvectl_status(st, OUTPUT_WITH_INTERFACE)
        # current_dns captura ambos (global + interface)
        assert "1.1.1.1" in st.current_dns
        assert "192.168.1.1" in st.current_dns


class TestParseMultipleInterfaces:
    def test_two_interfaces_parsed(self):
        st = ResolvedStatus()
        _parse_resolvectl_status(st, OUTPUT_MULTIPLE_INTERFACES)
        assert len(st.interfaces) == 2

        eth = next(i for i in st.interfaces if i.name == "eth0")
        wifi = next(i for i in st.interfaces if i.name == "wlp2s0")

        assert eth.dns_servers == ["192.168.1.1", "8.8.8.8"]
        assert eth.dns_over_tls == "yes"

        assert wifi.dns_servers == ["10.0.0.1"]
        assert wifi.dns_over_tls == "no"
        assert wifi.domains == ["corp.example.com"]


class TestParseEdgeCases:
    def test_no_dns_configured(self):
        st = ResolvedStatus()
        _parse_resolvectl_status(st, OUTPUT_NO_DNS_CONFIGURED)
        assert st.global_dns == []
        assert st.interfaces == []
        assert st.global_dot == "no"

    def test_dot_disabled(self):
        st = ResolvedStatus()
        _parse_resolvectl_status(st, OUTPUT_DOT_DISABLED)
        assert st.global_dns == ["8.8.8.8", "8.8.4.4"]
        assert st.global_dot == "no"

    def test_empty_input(self):
        st = ResolvedStatus()
        _parse_resolvectl_status(st, "")
        # Nao deve crashar
        assert st.global_dns == []
        assert st.interfaces == []

    def test_malformed_input_does_not_crash(self):
        st = ResolvedStatus()
        # Garbage que NAO deve crashar parser
        _parse_resolvectl_status(st, "random\nnoise\n\n\nmore\n")
        assert st.global_dns == []
