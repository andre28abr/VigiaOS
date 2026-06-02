"""Testes do backend do Vigia IDS (parser eve.json + cmd + análise)."""

from __future__ import annotations

import json

from vigia_blue.modules.ids import backend


def _alert_line(sig="ET SCAN Nmap", sev=2, src="1.2.3.4", sport=1234,
                dst="5.6.7.8", dport=80, cat="Attempted Information Leak"):
    return json.dumps({
        "timestamp": "2026-06-01T10:00:00.000+0000",
        "event_type": "alert",
        "src_ip": src, "src_port": sport, "dest_ip": dst, "dest_port": dport,
        "proto": "TCP",
        "alert": {"signature": sig, "category": cat, "severity": sev,
                  "signature_id": 2001},
    })


# ============================================================
# map_severity
# ============================================================


def test_map_severity():
    assert backend.map_severity(1) == "alto"
    assert backend.map_severity(2) == "suspeito"
    assert backend.map_severity(3) == "baixo"
    assert backend.map_severity(4) == "info"
    assert backend.map_severity("x") == "suspeito"   # inválido → default


# ============================================================
# parse_eve
# ============================================================


def test_parse_eve_alert():
    alerts = backend.parse_eve(_alert_line())
    assert len(alerts) == 1
    a = alerts[0]
    assert a.signature == "ET SCAN Nmap"
    assert a.severity == "suspeito"
    assert a.src == "1.2.3.4:1234" and a.dest == "5.6.7.8:80"
    assert a.proto == "TCP" and a.sid == 2001


def test_parse_eve_ignores_non_alert():
    flow = json.dumps({"event_type": "flow", "src_ip": "1.1.1.1"})
    dns = json.dumps({"event_type": "dns"})
    text = "\n".join([flow, _alert_line(), dns])
    assert len(backend.parse_eve(text)) == 1


def test_parse_eve_skips_garbage_lines():
    text = "\n".join(["isto não é json", "", _alert_line(), "{quebrado"])
    assert len(backend.parse_eve(text)) == 1


def test_parse_eve_missing_alert_dict():
    line = json.dumps({"event_type": "alert", "src_ip": "9.9.9.9"})
    alerts = backend.parse_eve(line)
    assert len(alerts) == 1
    assert alerts[0].signature == "(sem assinatura)"


def test_parse_eve_empty():
    assert backend.parse_eve("") == []
    assert backend.parse_eve(None) == []


def test_endpoint_without_port():
    line = json.dumps({"event_type": "alert", "src_ip": "9.9.9.9",
                       "alert": {"signature": "x", "severity": 1}})
    a = backend.parse_eve(line)[0]
    assert a.src == "9.9.9.9"   # sem porta


# ============================================================
# build_pcap_cmd
# ============================================================


def test_build_pcap_cmd():
    cmd = backend.build_pcap_cmd("/tmp/x.pcap", "/tmp/out")
    assert cmd == ["suricata", "-r", "/tmp/x.pcap", "-l", "/tmp/out"]
    assert isinstance(cmd, list)


def test_build_pcap_cmd_elevated():
    cmd = backend.build_pcap_cmd("/tmp/x.pcap", "/tmp/out", elevated=True)
    assert cmd[0] == "pkexec"
    assert "-r" in cmd and "/tmp/x.pcap" in cmd
    assert "-l" in cmd and "/tmp/out" in cmd


def test_needs_root():
    assert backend._needs_root(
        "failed to open file: /etc/suricata/suricata.yaml: Permission denied")
    assert backend._needs_root("Permission denied")
    assert not backend._needs_root("")
    assert not backend._needs_root("tudo certo, 3 alertas")


# ============================================================
# explain — descrição amigável "o que é"
# ============================================================


def _alert(sig="X", cat="", sev="baixo"):
    return backend.Alert("t", sig, cat, sev, "1.2.3.4:5", "6.7.8.9:80", "TCP", 1)


def test_explain_invalid_checksum():
    txt = backend.explain(_alert(sig="SURICATA UDPv4 invalid checksum",
                                 cat="Generic Protocol Command Decode")).lower()
    assert "checksum" in txt and ("artefato" in txt or "inofensivo" in txt)


def test_explain_by_category():
    txt = backend.explain(_alert(cat="Potentially Bad Traffic", sev="suspeito")).lower()
    assert "malicios" in txt or "falso positivo" in txt


def test_explain_fallback_by_severity():
    txt = backend.explain(_alert(cat="Categoria Inexistente ZZZ", sev="alto"))
    assert "ALTA" in txt or "prioridade" in txt.lower()


def test_explain_never_empty():
    # sempre retorna algo, mesmo sem categoria conhecida
    assert backend.explain(_alert(cat="", sev="info")).strip()


# ============================================================
# analyze_eve
# ============================================================


def test_analyze_eve_missing_file(tmp_path):
    res = backend.analyze_eve(tmp_path / "nao_existe.json")
    assert res.error and res.alerts == []


def test_analyze_eve_sorts_by_severity(tmp_path):
    eve = tmp_path / "eve.json"
    eve.write_text("\n".join([
        _alert_line(sig="baixa", sev=3),
        _alert_line(sig="alta", sev=1),
        _alert_line(sig="media", sev=2),
    ]))
    res = backend.analyze_eve(eve)
    assert len(res.alerts) == 3
    assert res.alerts[0].signature == "alta"          # mais severo primeiro
    ranks = [backend.SEVERITY_RANK[a.severity] for a in res.alerts]
    assert ranks == sorted(ranks, reverse=True)


def test_analyze_eve_max_alerts(tmp_path):
    eve = tmp_path / "eve.json"
    eve.write_text("\n".join(_alert_line() for _ in range(10)))
    res = backend.analyze_eve(eve, max_alerts=3)
    assert len(res.alerts) == 3


# ============================================================
# relatórios
# ============================================================


def test_save_and_list_report(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "REPORTS_DIR", tmp_path)
    res = backend.IdsResult(
        alerts=[backend.Alert("t", "sig", "cat", "alto", "a", "b", "TCP", 1)],
        source="/var/log/suricata/eve.json", total_lines=5,
        started_at="2026-06-01T10:00:00")
    path = backend.save_report(res)
    assert path is not None and path.exists()
    assert (path.stat().st_mode & 0o777) == 0o600
    recent = backend.list_recent_reports()
    assert len(recent) == 1 and recent[0]["alerts"][0]["severity"] == "alto"
