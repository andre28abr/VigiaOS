"""Smoke test de render ponta-a-ponta dos 2 templates.

Pega erros de template (Jinja), confirma que gráficos/status/resumo aparecem
e que dado do usuário é escapado. Não havia teste de render antes deste.
"""

from __future__ import annotations

from datetime import datetime

from vigia_reports import backend, renderer


def _period():
    return backend.Period(since=datetime(2026, 5, 24), until=datetime(2026, 5, 31))


def _activity_data():
    return {
        "period": _period(),
        "elevated_mode": True,
        "status": {"level": "warn", "label": "Atenção"},
        "summary": "Resumo de teste do período.",
        "kpis": {
            "ssh_success": 3, "ssh_failed": 142, "sudo_invocations": 12,
            "pkexec_invocations": 4, "bans": 5, "logins": 8,
        },
        "ssh_fails_by_day": [("24/05", 10), ("25/05", 30), ("26/05", 102)],
        "ssh_donut": [("Aceitos", 3, "#059669"), ("Falhados", 142, "#dc2626")],
        "ssh_success": [{"timestamp": "2026-05-30 10:00:00", "user": "andre", "ip": "10.0.0.1"}],
        "ssh_failed": [{"timestamp": "2026-05-30 11:00:00", "user": "root", "ip": "185.1.2.3"}],
        "sudo": [{"timestamp": "2026-05-30 12:00:00", "user": "andre", "target_user": "root", "command": "dnf update"}],
        "bans": [{"timestamp": "2026-05-30 13:00:00", "jail": "sshd", "ip": "185.1.2.3"}],
        "top_banned_ips": [("185.1.2.3", 48), ("91.4.5.6", 24)],
        "top_sudo_users": [("andre", 12)],
        "pkexec": [{"timestamp": "2026-05-30 14:00:00", "user": "andre", "command": "setenforce 1"}],
        "logins": [{"user": "andre", "tty": "tty1", "from": "", "when": "Fri May 30 09:00"}],
    }


def _auth_data():
    return {
        "period": _period(),
        "elevated_mode": False,
        "status": {"level": "ok", "label": "Sem anomalias"},
        "summary": "Tudo certo no período.",
        "kpis": {"ssh_success": 1, "ssh_failed": 0, "sudo_invocations": 0, "pkexec_invocations": 0, "bans": 0},
        "ssh_fails_by_day": [("24/05", 0), ("25/05", 0)],
        "ssh_donut": [("Aceitos", 1, "#059669"), ("Falhados", 0, "#dc2626")],
        "ssh_success": [], "ssh_failed": [], "sudo": [], "pkexec": [],
        "logins": [], "failed_logins": [],
    }


class TestRenderActivityOverview:
    def test_renders_full_document(self):
        html = renderer.render_html("activity_overview", _activity_data())
        assert "<!DOCTYPE html>" in html
        assert html.rstrip().endswith("</html>")

    def test_has_all_charts(self):
        html = renderer.render_html("activity_overview", _activity_data())
        # bar (falhas/dia) + donut + hbar (IPs) + hbar (sudo) = 4 SVGs
        assert html.count("<svg") >= 4

    def test_has_status_badge_and_summary(self):
        html = renderer.render_html("activity_overview", _activity_data())
        assert "status-badge warn" in html
        assert "Resumo de teste do período." in html

    def test_escapes_user_data(self):
        data = _activity_data()
        data["ssh_failed"] = [{"timestamp": "t", "user": "<script>evil", "ip": "1.2.3.4"}]
        html = renderer.render_html("activity_overview", data)
        assert "<script>evil" not in html


class TestRenderAuthEvents:
    def test_renders_full_document(self):
        html = renderer.render_html("auth_events", _auth_data())
        assert html.rstrip().endswith("</html>")
        assert "<svg" in html

    def test_status_ok_and_empty_states(self):
        html = renderer.render_html("auth_events", _auth_data())
        assert "status-badge ok" in html
        assert "empty" in html  # listas vazias → blocos .empty, sem crash
