"""Testes do consolidador Saúde do Sistema (system_health.py) — puros."""

from __future__ import annotations

from vigia_reports import system_health as sh


class TestLynis:
    def test_ok_with_date(self):
        r = sh._interpret_lynis(
            "hardening_index=78\nreport_datetime_end=2026-05-30 10:00:00\n"
        )
        assert r["state"] == "ok"
        assert "78/100" in r["headline"]
        assert r["ran_at"] == "2026-05-30 10:00:00"

    def test_warn(self):
        assert sh._interpret_lynis("hardening_index=60\n")["state"] == "warn"

    def test_danger(self):
        assert sh._interpret_lynis("hardening_index=40\n")["state"] == "danger"

    def test_missing_without_index(self):
        assert sh._interpret_lynis("lynis_version=3.0\n")["state"] == "missing"


class TestAntivirus:
    def test_clean(self):
        r = sh._interpret_antivirus(
            {"infected_files": 0, "scanned_files": 1200, "started_at": "2026-05-30 09:00:00"}
        )
        assert r["state"] == "ok"
        assert "Nenhuma ameaça" in r["headline"]

    def test_infected_is_danger(self):
        r = sh._interpret_antivirus({"infected_files": 3, "scanned_files": 1200})
        assert r["state"] == "danger"
        assert "3" in r["headline"]


class TestRootkit:
    def test_clean(self):
        r = sh._interpret_rootkit({"infected_count": 0, "warnings_count": 0, "scanner": "rkhunter"})
        assert r["state"] == "ok"
        assert "rkhunter" in r["label"]

    def test_warnings(self):
        assert sh._interpret_rootkit({"warnings_count": 5, "scanner": "rkhunter"})["state"] == "warn"

    def test_infected(self):
        assert sh._interpret_rootkit({"infected_count": 1, "scanner": "chkrootkit"})["state"] == "danger"


class TestIntegrity:
    def test_clean(self):
        st = {"baseline_exists": True,
              "last_check": {"timestamp": "t", "total_entries": 900, "added": 0, "removed": 0, "changed": 0}}
        assert sh._interpret_file_integrity(st)["state"] == "ok"

    def test_changes_warn(self):
        st = {"baseline_exists": True,
              "last_check": {"added": 2, "removed": 0, "changed": 1, "total_entries": 900}}
        r = sh._interpret_file_integrity(st)
        assert r["state"] == "warn"
        assert "3" in r["headline"]

    def test_missing_no_baseline(self):
        assert sh._interpret_file_integrity({})["state"] == "missing"

    def test_baseline_but_no_check(self):
        assert sh._interpret_file_integrity({"baseline_exists": True})["state"] == "warn"


def _entries(*states):
    return [
        {"label": f"d{i}", "state": s, "headline": "h", "detail": "d", "ran_at": "—"}
        for i, s in enumerate(states)
    ]


class TestScoreStatusSummary:
    def test_score(self):
        sc = sh.health_score(_entries("ok", "warn", "missing", "danger"))
        assert sc == {"total": 4, "ran": 3, "ok": 1, "issues": 2, "missing": 1}

    def test_status_danger(self):
        assert sh.health_status(_entries("ok", "danger"))["level"] == "danger"

    def test_status_warn(self):
        assert sh.health_status(_entries("ok", "warn"))["level"] == "warn"

    def test_status_ok(self):
        assert sh.health_status(_entries("ok", "ok"))["level"] == "ok"

    def test_status_all_missing_is_warn(self):
        assert sh.health_status(_entries("missing", "missing"))["level"] == "warn"

    def test_summary_mentions_counts_issues_missing(self):
        s = sh.health_summary(_entries("ok", "warn", "missing", "missing"))
        assert "2 de 4" in s
        assert "Requer atenção" in s
        assert "Ainda não executadas" in s


class TestCollectHealth:
    def test_returns_four_well_formed(self):
        entries = sh.collect_health()
        assert len(entries) == 4
        keys = {"tool", "label", "state", "headline", "detail", "ran_at"}
        assert all(keys <= set(e) for e in entries)
