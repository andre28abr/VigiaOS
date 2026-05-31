"""Testes do status/resumo executivo + bucketing por dia (backend)."""

from __future__ import annotations

from datetime import datetime

from vigia_reports import backend


class TestBuildStatus:
    def test_ok(self):
        st = backend.build_status({"ssh_failed": 2, "ssh_success": 1, "bans": 0})
        assert st["level"] == "ok"

    def test_warn_on_bans(self):
        st = backend.build_status({"ssh_failed": 0, "ssh_success": 0, "bans": 3})
        assert st["level"] == "warn"

    def test_warn_on_many_fails(self):
        st = backend.build_status({"ssh_failed": 25, "ssh_success": 0, "bans": 0})
        assert st["level"] == "warn"

    def test_danger_success_amid_bruteforce(self):
        st = backend.build_status({"ssh_failed": 80, "ssh_success": 2, "bans": 5})
        assert st["level"] == "danger"

    def test_all_levels_have_label(self):
        for kpis in (
            {"ssh_failed": 0, "ssh_success": 0, "bans": 0},
            {"ssh_failed": 30, "ssh_success": 0, "bans": 0},
            {"ssh_failed": 60, "ssh_success": 1, "bans": 0},
        ):
            assert backend.build_status(kpis)["label"]


class TestEventsByDay:
    def test_continuous_buckets(self):
        p = backend.Period(since=datetime(2026, 5, 1), until=datetime(2026, 5, 3))
        events = [
            {"timestamp": "2026-05-02 10:00:00"},
            {"timestamp": "2026-05-02 11:00:00"},
        ]
        out = backend.events_by_day(events, p)
        assert len(out) == 3  # 01, 02, 03 (inclusive)
        d = dict(out)
        assert d["02/05"] == 2
        assert d["01/05"] == 0
        assert d["03/05"] == 0

    def test_ignores_bad_timestamp(self):
        p = backend.Period(since=datetime(2026, 5, 1), until=datetime(2026, 5, 1))
        out = backend.events_by_day([{"timestamp": ""}, {"foo": "bar"}], p)
        assert out == [("01/05", 0)]


class TestBuildSummary:
    def _p(self):
        return backend.Period(since=datetime(2026, 5, 24), until=datetime(2026, 5, 31))

    def test_mentions_counts_and_blocked(self):
        kpis = {
            "ssh_success": 3, "ssh_failed": 142,
            "sudo_invocations": 12, "pkexec_invocations": 4, "bans": 5,
        }
        text = backend.build_summary(kpis, self._p(), backend.build_status(kpis))
        assert "3" in text and "142" in text
        assert "bloqueadas" in text  # bans > 0

    def test_singular_plural(self):
        kpis = {
            "ssh_success": 1, "ssh_failed": 0,
            "sudo_invocations": 1, "pkexec_invocations": 0, "bans": 0,
        }
        text = backend.build_summary(kpis, self._p(), backend.build_status(kpis))
        assert "acesso SSH bem-sucedido" in text  # singular
        assert "1 comando com sudo" in text

    def test_no_activity(self):
        kpis = {
            "ssh_success": 0, "ssh_failed": 0,
            "sudo_invocations": 0, "pkexec_invocations": 0, "bans": 0,
        }
        text = backend.build_summary(kpis, self._p(), backend.build_status(kpis))
        assert "não houve atividade" in text
        assert "Nenhuma anomalia" in text


class TestBuildHighlights:
    def test_quiet_period_single_bullet(self):
        out = backend.build_highlights(
            {"ssh_success": 0, "ssh_failed": 0, "sudo_invocations": 0, "pkexec_invocations": 0, "bans": 0}
        )
        assert len(out) == 1
        assert "tranquilo" in out[0]

    def test_busy_period(self):
        out = backend.build_highlights(
            {"ssh_success": 3, "ssh_failed": 142, "sudo_invocations": 10, "pkexec_invocations": 2, "bans": 5}
        )
        joined = " ".join(out)
        assert "fail2ban" in joined
        assert "142" in joined
        assert "12" in joined  # 10 sudo + 2 pkexec


class TestAdminStatusAndSummary:
    def _p(self):
        return backend.Period(since=datetime(2026, 5, 24), until=datetime(2026, 5, 31))

    def test_status_levels(self):
        assert backend.build_admin_status(0)["level"] == "ok"
        assert backend.build_admin_status(1)["level"] == "ok"
        assert backend.build_admin_status(3)["level"] == "warn"
        assert "3" in backend.build_admin_status(3)["label"]

    def test_summary_no_activity(self):
        text = backend.build_admin_summary(
            {"sudo_invocations": 0, "pkexec_invocations": 0, "admin_total": 0, "admin_users": 0},
            self._p(),
        )
        assert "nenhum comando administrativo" in text

    def test_summary_multi_user_lgpd_note(self):
        text = backend.build_admin_summary(
            {"sudo_invocations": 10, "pkexec_invocations": 2, "admin_total": 12, "admin_users": 2},
            self._p(),
        )
        assert "12" in text
        assert "menor privilégio" in text
