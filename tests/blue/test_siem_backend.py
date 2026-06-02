"""Testes do backend do Vigia SIEM (motor de detecção puro, sem gi/vigia-log).

Cobre: parser do bundle, helpers de payload, cada regra de detecção (caso
positivo + negativo), o motor `detect` (ordenação/robustez/correlações),
catálogo de regras e relatórios (0600).
"""

from __future__ import annotations

import json

import pytest

from vigia_blue.modules.siem import backend


# ============================================================
# Fábricas de eventos (espelham o payload do core)
# ============================================================


def audit_ev(records, ts="2026-06-01 10:00:00", severity="suspicious"):
    """records = [(record_type, {campos})] ou um único (tipo, campos)."""
    if isinstance(records, tuple):
        records = [records]
    payload = {
        "source": "audit",
        "records": [{"record_type": rt, "fields": f} for rt, f in records],
    }
    return backend.Event(timestamp=ts, source="audit", severity=severity,
                         narrative=f"audit {records[0][0]}", payload=payload)


def journal_ev(message, comm="", unit="", priority="info",
               ts="2026-06-01 10:00:00", severity="interesting"):
    return backend.Event(
        timestamp=ts, source="journal", severity=severity, narrative=message,
        payload={"source": "journal", "message": message, "comm": comm,
                 "unit": unit, "priority": priority})


def f2b_ev(kind, ip="", jail="", ts="2026-06-01 10:00:00", severity="suspicious"):
    return backend.Event(
        timestamp=ts, source="fail2ban", severity=severity,
        narrative=f"fail2ban {kind} {ip}",
        payload={"source": "fail2ban", "action": {"kind": kind}, "ip": ip,
                 "jail": jail, "raw_message": f"{kind} {ip} {jail}"})


# ============================================================
# parse_bundle + helpers
# ============================================================


def test_parse_bundle_valid():
    data = {
        "events": [
            {"timestamp": "t1", "source": "journal", "severity": "interesting",
             "narrative": "n", "payload": {"message": "oi"}},
        ],
        "correlations": [{"kind": "k", "severity": "suspicious", "summary": "s"}],
    }
    events, corrs = backend.parse_bundle(data)
    assert len(events) == 1 and events[0].source == "journal"
    assert events[0].payload["message"] == "oi"
    assert len(corrs) == 1 and corrs[0]["kind"] == "k"


def test_parse_bundle_garbage_never_crashes():
    assert backend.parse_bundle(None) == ([], [])
    assert backend.parse_bundle({"events": "nope"}) == ([], [])
    assert backend.parse_bundle({}) == ([], [])
    # evento não-dict é ignorado; payload não-dict vira {}
    events, _ = backend.parse_bundle({"events": ["x", {"payload": 7}]})
    assert len(events) == 1 and events[0].payload == {}


def test_audit_field_and_primary_type():
    ev = audit_ev([("SYSCALL", {"success": "yes"}),
                   ("AVC", {"permissive": "0"})])
    assert backend._audit_primary_type(ev) == "AVC"   # AVC tem prioridade
    assert backend._audit_field(ev, "permissive") == "0"
    assert backend._audit_field(ev, "inexistente") is None


def test_is_failure():
    assert backend._is_failure("failed") is True
    assert backend._is_failure("0") is True
    assert backend._is_failure("success") is False
    assert backend._is_failure("1") is False
    assert backend._is_failure(None) is False
    assert backend._is_failure("") is False


# ============================================================
# Regra: ssh_bruteforce
# ============================================================


def test_ssh_bruteforce_audit_threshold():
    evs = [audit_ev(("USER_AUTH", {"res": "failed", "addr": "203.0.113.5"}))
           for _ in range(5)]
    alerts = backend._r_ssh_bruteforce(evs)
    assert len(alerts) == 1
    assert alerts[0].severity == "alto"
    assert alerts[0].count == 5
    assert "203.0.113.5" in alerts[0].title


def test_ssh_bruteforce_below_threshold_no_alert():
    evs = [audit_ev(("USER_AUTH", {"res": "failed", "addr": "203.0.113.5"}))
           for _ in range(4)]
    assert backend._r_ssh_bruteforce(evs) == []


def test_ssh_bruteforce_critico_above_20():
    evs = [audit_ev(("USER_AUTH", {"res": "failed", "addr": "10.0.0.9"}))
           for _ in range(20)]
    assert backend._r_ssh_bruteforce(evs)[0].severity == "critico"


def test_ssh_bruteforce_success_not_counted():
    evs = [audit_ev(("USER_AUTH", {"res": "success", "addr": "10.0.0.1"}))
           for _ in range(10)]
    assert backend._r_ssh_bruteforce(evs) == []


def test_ssh_bruteforce_journal_extracts_ip():
    msg = "Failed password for invalid user root from 198.51.100.7 port 22 ssh2"
    evs = [journal_ev(msg, comm="sshd") for _ in range(6)]
    alerts = backend._r_ssh_bruteforce(evs)
    assert len(alerts) == 1
    assert "198.51.100.7" in alerts[0].title


# ============================================================
# Regra: failed_sudo
# ============================================================


def test_failed_sudo_audit():
    evs = [audit_ev(("USER_CMD", {"exe": "/usr/bin/sudo", "res": "failed"}))]
    alerts = backend._r_failed_sudo(evs)
    assert len(alerts) == 1 and alerts[0].severity == "suspeito"


def test_failed_sudo_journal():
    evs = [journal_ev("pam_unix(sudo:auth): authentication failure; user=bob",
                      comm="sudo")]
    assert len(backend._r_failed_sudo(evs)) == 1


def test_failed_sudo_success_ignored():
    evs = [audit_ev(("USER_CMD", {"exe": "/usr/bin/sudo", "res": "success"}))]
    assert backend._r_failed_sudo(evs) == []


def test_failed_sudo_high_when_many():
    evs = [audit_ev(("USER_CMD", {"exe": "/usr/bin/sudo", "res": "failed"}))
           for _ in range(5)]
    assert backend._r_failed_sudo(evs)[0].severity == "alto"


# ============================================================
# Regra: account_change
# ============================================================


def test_account_change_audit():
    evs = [audit_ev(("ADD_USER", {"acct": "intruso"}))]
    alerts = backend._r_account_change(evs)
    assert len(alerts) == 1 and alerts[0].severity == "suspeito"


def test_account_change_journal_comm():
    evs = [journal_ev("new user: name=intruso", comm="useradd")]
    assert len(backend._r_account_change(evs)) == 1


def test_account_change_none():
    assert backend._r_account_change([journal_ev("nada a ver")]) == []


# ============================================================
# Regra: service_failure
# ============================================================


def test_service_failure_message():
    evs = [journal_ev("Failed to start Nginx.", unit="nginx.service", priority="err")]
    alerts = backend._r_service_failure(evs)
    assert len(alerts) == 1
    assert "nginx.service" in alerts[0].description


def test_service_failure_audit():
    evs = [audit_ev(("SERVICE_STOP", {"res": "failed", "unit": "x"}))]
    assert len(backend._r_service_failure(evs)) == 1


def test_service_failure_routine_ignored():
    evs = [journal_ev("Started Nginx.", unit="nginx.service", priority="info")]
    assert backend._r_service_failure(evs) == []


# ============================================================
# Regra: selinux_denial
# ============================================================


def test_selinux_enforcing_suspeito():
    evs = [audit_ev(("AVC", {"permissive": "0", "comm": "httpd"}))]
    alerts = backend._r_selinux_denial(evs)
    assert len(alerts) == 1 and alerts[0].severity == "suspeito"


def test_selinux_permissive_baixo():
    evs = [audit_ev(("AVC", {"permissive": "1", "comm": "httpd"}))]
    alerts = backend._r_selinux_denial(evs)
    assert len(alerts) == 1 and alerts[0].severity == "baixo"


def test_selinux_both_buckets():
    evs = [audit_ev(("AVC", {"permissive": "0"})),
           audit_ev(("AVC", {"permissive": "1"}))]
    alerts = backend._r_selinux_denial(evs)
    assert len(alerts) == 2
    assert {a.severity for a in alerts} == {"suspeito", "baixo"}


# ============================================================
# Regra: package_change
# ============================================================


def test_package_change_comm():
    evs = [journal_ev("Upgraded: kernel", comm="rpm-ostree")]
    alerts = backend._r_package_change(evs)
    assert len(alerts) == 1 and alerts[0].severity == "info"


def test_package_change_keyword():
    evs = [journal_ev("Installed: curl-8.0", comm="x")]
    assert len(backend._r_package_change(evs)) == 1


# ============================================================
# Regra: fail2ban_ban
# ============================================================


def test_fail2ban_ban():
    evs = [f2b_ev("ban", ip="203.0.113.9", jail="sshd")]
    alerts = backend._r_fail2ban_ban(evs)
    assert len(alerts) == 1 and alerts[0].severity == "suspeito"
    assert "203.0.113.9" in alerts[0].description


def test_fail2ban_found_not_ban():
    assert backend._r_fail2ban_ban([f2b_ev("found", ip="1.1.1.1")]) == []


# ============================================================
# Motor detect()
# ============================================================


def test_detect_sorts_by_severity_desc():
    evs = [
        journal_ev("Installed: curl", comm="rpm-ostree"),     # info
        *[audit_ev(("USER_AUTH", {"res": "failed", "addr": "9.9.9.9"}))
          for _ in range(5)],                                  # alto
        f2b_ev("ban", ip="8.8.8.8", jail="sshd"),              # suspeito
    ]
    alerts = backend.detect(evs)
    sevs = [a.severity for a in alerts]
    ranks = [backend.SEVERITY_RANK[s] for s in sevs]
    assert ranks == sorted(ranks, reverse=True)
    assert sevs[0] == "alto"


def test_detect_includes_correlations():
    corr = {"kind": "ssh_burst", "severity": "suspicious",
            "summary": "rajada", "contributing_count": 3}
    alerts = backend.detect([], [corr])
    assert any(a.rule_id == "correlation" and a.severity == "suspeito"
               for a in alerts)


def test_detect_robust_to_bad_payload():
    bad = backend.Event(timestamp="t", source="audit", severity="x",
                        narrative="", payload=None)  # payload inválido
    # não deve levantar
    assert isinstance(backend.detect([bad]), list)


def test_detect_empty():
    assert backend.detect([]) == []


def test_severity_counts():
    evs = [*[audit_ev(("USER_AUTH", {"res": "failed", "addr": "9.9.9.9"}))
             for _ in range(5)],
           journal_ev("Installed: x", comm="dnf")]
    counts = backend.severity_counts(backend.detect(evs))
    assert counts.get("alto") == 1
    assert counts.get("info") == 1


# ============================================================
# Catálogo de regras
# ============================================================


def test_rules_catalog_shape():
    rules = backend.rules_catalog()
    assert len(rules) == 7
    ids = [r.id for r in rules]
    assert len(set(ids)) == 7                       # ids únicos
    assert set(ids) == set(backend._MATCHERS)       # catálogo == matchers
    for r in rules:
        assert r.name and r.description and r.recommendation
        assert r.sources
        assert r.severity in backend.SEVERITY_RANK


# ============================================================
# Coleta sem o core instalado
# ============================================================


def test_collect_without_core(monkeypatch):
    monkeypatch.setattr(backend.shutil, "which", lambda _name: None)
    data, err = backend.collect()
    assert data is None and "vigia-log" in err


def test_analyze_without_core(monkeypatch):
    monkeypatch.setattr(backend.shutil, "which", lambda _name: None)
    res = backend.analyze()
    assert res.error and res.events_count == 0 and res.alerts == []


# ============================================================
# Relatórios (0600)
# ============================================================


def test_save_and_list_reports(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "REPORTS_DIR", tmp_path)
    res = backend.SiemResult(
        alerts=[backend.Alert("ssh_bruteforce", "t", "d", "r", "alto", 5,
                              "quando", ["ev1"])],
        events_count=10, sources=["journald"], started_at="2026-06-01T10:00:00")
    path = backend.save_report(res)
    assert path is not None and path.exists()
    # permissão 0600
    assert (path.stat().st_mode & 0o777) == 0o600
    saved = json.loads(path.read_text())
    assert saved["alerts"][0]["severity"] == "alto"

    recent = backend.list_recent_reports()
    assert len(recent) == 1 and recent[0]["events_count"] == 10


def test_list_reports_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "REPORTS_DIR", tmp_path / "vazio")
    assert backend.list_recent_reports() == []
