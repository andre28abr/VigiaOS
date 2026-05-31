"""Testes das checagens de Conformidade LGPD (compliance.py) — puros."""

from __future__ import annotations

from vigia_reports import compliance


class TestInterpreters:
    def test_service_active_good(self):
        assert compliance._state_service("active", True) == "ok"
        assert compliance._state_service("inactive", True) == "off"

    def test_service_active_bad(self):
        # sshd: ativo = atenção (mais superfície), inativo = ok
        assert compliance._state_service("active", False) == "warn"
        assert compliance._state_service("inactive", False) == "ok"

    def test_service_unknown(self):
        assert compliance._state_service("", True) == "unknown"

    def test_selinux(self):
        assert compliance._state_selinux("Enforcing") == "ok"
        assert compliance._state_selinux("Permissive") == "warn"
        assert compliance._state_selinux("Disabled") == "off"
        assert compliance._state_selinux("") == "unknown"

    def test_gsettings(self):
        assert compliance._state_gsettings("false", "false") == "ok"
        assert compliance._state_gsettings("true", "false") == "warn"
        assert compliance._state_gsettings("'algo'", "false") == "unknown"

    def test_disk(self):
        assert compliance._state_disk("TYPE\ndisk\ncrypt\npart") == "ok"
        assert compliance._state_disk("TYPE\ndisk\npart") == "warn"
        assert compliance._state_disk("") == "unknown"


def _mk(state, critical=False, label="x"):
    return {"label": label, "state": state, "critical": critical}


class TestScoreStatusSummary:
    def test_score_excludes_unknown(self):
        checks = [_mk("ok"), _mk("warn"), _mk("unknown")]
        sc = compliance.compliance_score(checks)
        assert sc["ok"] == 1
        assert sc["total"] == 2  # unknown não conta
        assert sc["pct"] == 50
        assert sc["unknown"] == 1

    def test_status_danger_on_critical_fail(self):
        checks = [_mk("off", critical=True), _mk("ok")]
        assert compliance.compliance_status(checks)["level"] == "danger"

    def test_status_warn_on_noncritical_fail(self):
        checks = [_mk("warn"), _mk("ok")]
        assert compliance.compliance_status(checks)["level"] == "warn"

    def test_status_ok_all_good(self):
        checks = [_mk("ok", critical=True), _mk("ok")]
        assert compliance.compliance_status(checks)["level"] == "ok"

    def test_status_unknown_is_neutral(self):
        # unknown não derruba o status
        assert compliance.compliance_status([_mk("ok"), _mk("unknown")])["level"] == "ok"

    def test_summary_lists_failures(self):
        checks = [
            {"label": "Firewall", "state": "off", "critical": True},
            {"label": "DNS encriptado", "state": "ok", "critical": False},
        ]
        s = compliance.compliance_summary(checks)
        assert "1 de 2" in s
        assert "Firewall" in s


class TestRunChecks:
    def test_smoke_with_fake_commands(self, monkeypatch):
        monkeypatch.setattr(compliance.shutil, "which", lambda b: "/usr/bin/" + b)

        def fake_run(cmd, timeout=10):
            c = " ".join(cmd)
            if "getenforce" in c:
                return "Enforcing"
            if "lsblk" in c:
                return "TYPE\ndisk\ncrypt\npart"
            if "gsettings" in c:
                # location/telemetry esperam 'false', lock espera 'true'
                return "true" if "screensaver" in c else "false"
            if "is-active" in c:
                unit = cmd[-1]
                return "active" if unit in ("firewalld", "dnscrypt-proxy") else "inactive"
            return ""

        monkeypatch.setattr(compliance, "_run", fake_run)
        checks = compliance.run_compliance_checks()
        assert len(checks) == 9
        assert all({"label", "state", "value", "detail", "critical"} <= set(c) for c in checks)
        by_label = {c["label"]: c for c in checks}
        assert by_label["Firewall (firewalld)"]["state"] == "ok"
        assert by_label["Disco criptografado (LUKS)"]["state"] == "ok"
        assert by_label["Servidor SSH (entrada)"]["state"] == "ok"        # inativo = bom
        assert by_label["Proteção contra força bruta (fail2ban)"]["state"] == "off"
        assert by_label["Bloqueio de tela automático"]["state"] == "ok"   # true = bom
