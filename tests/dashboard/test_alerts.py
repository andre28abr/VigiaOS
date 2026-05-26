"""Testes para vigia_dashboard.alerts.

Testa AlertManager logic: duration_sec, cooldown_sec, op gt/lt, reset
de state quando desabilita.

NAO testa Gio.Notification (precisa GTK + display).
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from vigia_dashboard.alerts import (
    METRICS,
    AlertEvent,
    AlertManager,
    AlertRule,
    metric_label,
    new_rule_id,
)


# ============================================================
# AlertRule + helpers
# ============================================================


class TestMetricsMetadata:
    def test_all_metrics_have_label(self):
        for key, meta in METRICS.items():
            assert "label" in meta
            assert isinstance(meta["label"], str)
            assert len(meta["label"]) > 0

    def test_all_metrics_have_default_threshold(self):
        for key, meta in METRICS.items():
            assert "default_threshold" in meta
            assert isinstance(meta["default_threshold"], (int, float))

    def test_all_metrics_have_range(self):
        for key, meta in METRICS.items():
            assert "range" in meta
            lo, hi = meta["range"]
            assert lo <= hi

    def test_metric_label_known(self):
        # cpu_pct existe no dict
        assert metric_label("cpu_pct") == METRICS["cpu_pct"]["label"]

    def test_metric_label_unknown(self):
        # Unknown — retorna o proprio id
        assert metric_label("foo_bar") == "foo_bar"


class TestNewRuleId:
    def test_returns_hex_string(self):
        rid = new_rule_id()
        assert isinstance(rid, str)
        assert len(rid) == 32  # uuid4 hex
        # Apenas chars hex
        int(rid, 16)  # raise se nao for hex

    def test_unique(self):
        ids = [new_rule_id() for _ in range(100)]
        assert len(set(ids)) == 100


# ============================================================
# AlertManager — fixtures de regras simples
# ============================================================


@pytest.fixture
def cpu_rule():
    return AlertRule(
        id="rule-cpu",
        metric="cpu_pct",
        threshold=80.0,
        op="gt",
        duration_sec=5,
        cooldown_sec=60,
        label="High CPU",
        enabled=True,
    )


@pytest.fixture
def temp_rule_lt():
    return AlertRule(
        id="rule-temp-low",
        metric="cpu_temp_c",
        threshold=10.0,
        op="lt",
        duration_sec=2,
        cooldown_sec=30,
        label="Low temp (anomaly)",
        enabled=True,
    )


# ============================================================
# AlertManager tests
# ============================================================


class TestAlertManagerBasics:
    def test_empty_manager(self):
        mgr = AlertManager()
        assert mgr.check({"cpu_pct": 99.0}) == []

    def test_no_rules_no_alerts(self):
        mgr = AlertManager()
        mgr.set_rules([])
        assert mgr.check({"cpu_pct": 99.0}) == []

    def test_set_rules_replaces(self, cpu_rule):
        mgr = AlertManager()
        mgr.set_rules([cpu_rule])
        assert len(mgr.get_rules()) == 1
        mgr.set_rules([])
        assert len(mgr.get_rules()) == 0


class TestAlertManagerGreaterThan:
    def test_below_threshold_no_alert(self, cpu_rule):
        mgr = AlertManager()
        mgr.set_rules([cpu_rule])
        assert mgr.check({"cpu_pct": 50.0}) == []

    def test_above_threshold_needs_duration(self, cpu_rule):
        """Acima do threshold imediatamente nao dispara (duration_sec=5)."""
        mgr = AlertManager()
        mgr.set_rules([cpu_rule])
        # Primeira call: comeca a contar
        assert mgr.check({"cpu_pct": 95.0}) == []
        # Segunda call imediata: ainda nao passou duration
        assert mgr.check({"cpu_pct": 95.0}) == []

    def test_above_threshold_for_duration_fires(self, cpu_rule):
        """Apos duration_sec, dispara."""
        mgr = AlertManager()
        mgr.set_rules([cpu_rule])

        # Simula tempo passando via mock de time.time
        with patch("vigia_dashboard.alerts.time.time") as mock_time:
            mock_time.return_value = 1000.0
            assert mgr.check({"cpu_pct": 95.0}) == []  # comeca contar

            # 6 segundos depois (duration_sec=5)
            mock_time.return_value = 1006.0
            events = mgr.check({"cpu_pct": 95.0})
            assert len(events) == 1
            assert events[0].rule_id == cpu_rule.id
            assert events[0].current_value == 95.0
            assert events[0].threshold == 80.0

    def test_cooldown_prevents_re_fire(self, cpu_rule):
        mgr = AlertManager()
        mgr.set_rules([cpu_rule])

        with patch("vigia_dashboard.alerts.time.time") as mock_time:
            mock_time.return_value = 1000.0
            mgr.check({"cpu_pct": 95.0})
            mock_time.return_value = 1006.0
            events1 = mgr.check({"cpu_pct": 95.0})
            assert len(events1) == 1  # disparou

            # Imediatamente apos: cooldown ativo
            mock_time.return_value = 1010.0
            events2 = mgr.check({"cpu_pct": 95.0})
            assert len(events2) == 0

            # Apos cooldown (60s)
            mock_time.return_value = 1080.0
            events3 = mgr.check({"cpu_pct": 95.0})
            assert len(events3) == 1


class TestAlertManagerLessThan:
    def test_lt_op(self, temp_rule_lt):
        """op=lt dispara quando valor < threshold."""
        mgr = AlertManager()
        mgr.set_rules([temp_rule_lt])

        with patch("vigia_dashboard.alerts.time.time") as mock_time:
            mock_time.return_value = 2000.0
            # Acima threshold = ok (lt requer ESTAR ABAIXO pra disparar)
            assert mgr.check({"cpu_temp_c": 45.0}) == []

            # Abaixo threshold — comeca contar
            assert mgr.check({"cpu_temp_c": 5.0}) == []
            mock_time.return_value = 2003.0  # 3 segundos depois (duration=2)
            events = mgr.check({"cpu_temp_c": 5.0})
            assert len(events) == 1


class TestAlertManagerReset:
    def test_reset_when_back_to_normal(self, cpu_rule):
        """Se volta abaixo do threshold, contador reseta."""
        mgr = AlertManager()
        mgr.set_rules([cpu_rule])

        with patch("vigia_dashboard.alerts.time.time") as mock_time:
            mock_time.return_value = 1000.0
            mgr.check({"cpu_pct": 95.0})

            # Volta abaixo — reseta
            mock_time.return_value = 1003.0
            mgr.check({"cpu_pct": 50.0})

            # Sobe de novo — comeca a contar do zero, NAO dispara em 1003+1=1004
            mock_time.return_value = 1004.0
            assert mgr.check({"cpu_pct": 95.0}) == []

            # Precisa de outros 5s (duration_sec)
            mock_time.return_value = 1010.0
            events = mgr.check({"cpu_pct": 95.0})
            assert len(events) == 1

    def test_disabled_rule_does_not_fire(self, cpu_rule):
        cpu_rule.enabled = False
        mgr = AlertManager()
        mgr.set_rules([cpu_rule])

        with patch("vigia_dashboard.alerts.time.time") as mock_time:
            mock_time.return_value = 1000.0
            mgr.check({"cpu_pct": 99.0})
            mock_time.return_value = 1100.0
            events = mgr.check({"cpu_pct": 99.0})
            assert events == []


class TestAlertManagerMissingMetric:
    def test_missing_metric_does_not_crash(self, cpu_rule):
        """Se metrica nao esta no snapshot, nao dispara nem crasha."""
        mgr = AlertManager()
        mgr.set_rules([cpu_rule])
        # Snapshot sem cpu_pct
        events = mgr.check({"mem_pct": 50.0})
        assert events == []


class TestAlertManagerMultipleRules:
    def test_two_rules_independent(self, cpu_rule, temp_rule_lt):
        mgr = AlertManager()
        mgr.set_rules([cpu_rule, temp_rule_lt])

        with patch("vigia_dashboard.alerts.time.time") as mock_time:
            mock_time.return_value = 1000.0
            mgr.check({"cpu_pct": 95.0, "cpu_temp_c": 5.0})

            # Ambas ativadas no mesmo tempo
            mock_time.return_value = 1003.0  # temp duration=2 — temp dispara
            events = mgr.check({"cpu_pct": 95.0, "cpu_temp_c": 5.0})
            assert len(events) == 1
            assert events[0].metric == "cpu_temp_c"

            # CPU dispara depois
            mock_time.return_value = 1006.0  # cpu duration=5 — agora dispara
            events = mgr.check({"cpu_pct": 95.0, "cpu_temp_c": 5.0})
            # Pode dispara cpu novamente; temp esta em cooldown (30s)
            cpu_events = [e for e in events if e.metric == "cpu_pct"]
            assert len(cpu_events) == 1
