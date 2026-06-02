"""Testes do backend do Vigia Intel (classificação, checagem, import, base)."""

from __future__ import annotations

import json

from vigia_blue.modules.intel import backend


# ============================================================
# detect_type / normalize
# ============================================================


def test_detect_type_ip():
    assert backend.detect_type("203.0.113.5") == ("ip", "203.0.113.5")


def test_detect_type_hashes():
    assert backend.detect_type("d41d8cd98f00b204e9800998ecf8427e")[0] == "hash"   # md5
    assert backend.detect_type("a" * 40)[0] == "hash"                              # sha1
    assert backend.detect_type("b" * 64)[0] == "hash"                              # sha256


def test_detect_type_domain_url_email():
    assert backend.detect_type("Evil.COM") == ("domain", "evil.com")
    assert backend.detect_type("http://Bad.com/x")[0] == "url"
    assert backend.detect_type("a@b.com")[0] == "email"


def test_detect_type_empty_and_other():
    assert backend.detect_type("") == ("other", "")
    assert backend.detect_type("just words")[0] == "other"


# ============================================================
# check
# ============================================================


def test_check_ip_and_hash_match():
    iocs = [backend.IOC("ip", "203.0.113.5", "OTX"),
            backend.IOC("hash", "a" * 32, "MISP")]
    matches = backend.check(["203.0.113.5", "a" * 32, "8.8.8.8"], iocs)
    vals = {m.ioc.value for m in matches}
    assert vals == {"203.0.113.5", "a" * 32}


def test_check_url_matches_domain_host():
    iocs = [backend.IOC("domain", "evil.com", "manual")]
    matches = backend.check(["https://evil.com/payload"], iocs)
    assert len(matches) == 1 and matches[0].ioc.value == "evil.com"


def test_check_no_match():
    iocs = [backend.IOC("ip", "1.1.1.1", "x")]
    assert backend.check(["2.2.2.2"], iocs) == []


def test_check_empty_indicators():
    assert backend.check([], [backend.IOC("ip", "1.1.1.1", "x")]) == []


# ============================================================
# import
# ============================================================


def test_import_plain_dedupe_and_comments():
    text = "203.0.113.5\n# comentário\nevil.com\n203.0.113.5\n\n"
    iocs = backend.import_plain(text)
    assert len(iocs) == 2
    assert {i.type for i in iocs} == {"ip", "domain"}


def test_parse_otx_pulse():
    data = {"indicators": [
        {"indicator": "203.0.113.5", "type": "IPv4", "description": "c2"},
        {"indicator": "evil.com", "type": "domain"},
        {"indicator": "", "type": "domain"},   # ignorado
    ]}
    iocs = backend.parse_otx_pulse(data)
    assert len(iocs) == 2
    assert all(i.source == "OTX" for i in iocs)


def test_parse_otx_garbage():
    assert backend.parse_otx_pulse(None) == []
    assert backend.parse_otx_pulse({"indicators": "x"}) == []


def test_parse_misp_event():
    data = {"Event": {"Attribute": [
        {"type": "ip-dst", "value": "203.0.113.9"},
        {"type": "md5", "value": "a" * 32},
        {"type": "comment", "value": ""},   # ignorado
    ]}}
    iocs = backend.parse_misp_event(data)
    assert len(iocs) == 2 and all(i.source == "MISP" for i in iocs)


def test_parse_misp_garbage():
    assert backend.parse_misp_event(None) == []
    assert backend.parse_misp_event({"Event": {"Attribute": "x"}}) == []


# ============================================================
# base local (0600)
# ============================================================


def _patch_store(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "DATA_DIR", tmp_path)
    monkeypatch.setattr(backend, "STORE", tmp_path / "iocs.json")


def test_add_load_save_iocs(tmp_path, monkeypatch):
    _patch_store(tmp_path, monkeypatch)
    added = backend.add_iocs([backend.IOC("ip", "203.0.113.5", "manual")])
    assert added == 1
    iocs = backend.load_iocs()
    assert len(iocs) == 1 and iocs[0].value == "203.0.113.5"
    assert iocs[0].added_at  # carimbado ao adicionar
    assert (backend.STORE.stat().st_mode & 0o777) == 0o600


def test_add_iocs_dedupe(tmp_path, monkeypatch):
    _patch_store(tmp_path, monkeypatch)
    backend.add_iocs([backend.IOC("ip", "1.1.1.1", "a")])
    added = backend.add_iocs([backend.IOC("ip", "1.1.1.1", "b"),
                              backend.IOC("ip", "2.2.2.2", "c")])
    assert added == 1   # só o novo
    assert backend.stats()["total"] == 2


def test_remove_ioc(tmp_path, monkeypatch):
    _patch_store(tmp_path, monkeypatch)
    backend.add_iocs([backend.IOC("ip", "1.1.1.1", "a"),
                      backend.IOC("ip", "2.2.2.2", "b")])
    removed = backend.remove_ioc("1.1.1.1")
    assert removed == 1 and backend.stats()["total"] == 1


def test_stats(tmp_path, monkeypatch):
    _patch_store(tmp_path, monkeypatch)
    backend.add_iocs([backend.IOC("ip", "1.1.1.1", "a"),
                      backend.IOC("domain", "evil.com", "b")])
    st = backend.stats()
    assert st["total"] == 2 and st["ip"] == 1 and st["domain"] == 1


def test_load_iocs_empty(tmp_path, monkeypatch):
    _patch_store(tmp_path, monkeypatch)
    assert backend.load_iocs() == []


def test_roundtrip_via_json(tmp_path, monkeypatch):
    _patch_store(tmp_path, monkeypatch)
    backend.add_iocs([backend.IOC("hash", "a" * 64, "OTX", "dropper")])
    raw = json.loads(backend.STORE.read_text())
    assert raw[0]["note"] == "dropper" and raw[0]["type"] == "hash"
