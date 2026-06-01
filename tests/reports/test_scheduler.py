"""Testes do agendador (scheduler.py) — construtores de unit puros + parsing."""

from __future__ import annotations

from vigia_reports import scheduler


class TestUnitBuilders:
    def test_service_unit_execstart(self):
        u = scheduler.build_service_unit("lgpd_compliance", 30, "/usr/bin/vigia-reports")
        assert "Type=oneshot" in u
        assert (
            "ExecStart=/usr/bin/vigia-reports --generate lgpd_compliance --period 30"
            in u
        )

    def test_timer_unit_monthly_persistent(self):
        u = scheduler.build_timer_unit()
        assert "OnCalendar=" in u
        assert "Persistent=true" in u
        assert "WantedBy=timers.target" in u


class TestScheduledModel:
    def test_reads_model_from_service(self, tmp_path, monkeypatch):
        svc = tmp_path / "vigia-reports.service"
        svc.write_text(
            scheduler.build_service_unit("system_health", 30, "/x/vigia-reports"),
            encoding="utf-8",
        )
        monkeypatch.setattr(scheduler, "SERVICE", svc)
        assert scheduler.scheduled_model() == "system_health"

    def test_none_when_no_service(self, tmp_path, monkeypatch):
        monkeypatch.setattr(scheduler, "SERVICE", tmp_path / "ausente.service")
        assert scheduler.scheduled_model() is None
