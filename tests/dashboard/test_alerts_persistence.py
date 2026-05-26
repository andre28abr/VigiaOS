"""Testes de persistencia em vigia_dashboard.alerts.

Testa load_rules, save_rules, _default_rules — IO real em tmp_path.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from vigia_dashboard import alerts as alerts_mod
from vigia_dashboard.alerts import AlertRule


@pytest.fixture
def tmp_config_dir(tmp_path, monkeypatch):
    """Substitui CONFIG_DIR e CONFIG_PATH para usar tmp_path."""
    fake_dir = tmp_path / "config"
    fake_path = fake_dir / "dashboard-alerts.json"
    monkeypatch.setattr(alerts_mod, "CONFIG_DIR", fake_dir)
    monkeypatch.setattr(alerts_mod, "CONFIG_PATH", fake_path)
    yield fake_dir, fake_path


class TestLoadRules:
    def test_missing_file_returns_defaults(self, tmp_config_dir):
        fake_dir, fake_path = tmp_config_dir
        # Arquivo nao existe
        rules = alerts_mod.load_rules()
        # Default rules sao retornadas
        assert len(rules) > 0
        # Default rules sao opt-in (enabled=False)
        for rule in rules:
            assert rule.enabled is False

    def test_loads_existing_rules(self, tmp_config_dir):
        fake_dir, fake_path = tmp_config_dir
        fake_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "rules": [
                {
                    "id": "myrule",
                    "metric": "cpu_pct",
                    "threshold": 70.0,
                    "op": "gt",
                    "duration_sec": 30,
                    "cooldown_sec": 60,
                    "label": "Test",
                    "enabled": True,
                }
            ]
        }
        fake_path.write_text(json.dumps(data))

        rules = alerts_mod.load_rules()
        assert len(rules) == 1
        assert rules[0].id == "myrule"
        assert rules[0].threshold == 70.0
        assert rules[0].enabled is True

    def test_malformed_json_returns_defaults(self, tmp_config_dir):
        fake_dir, fake_path = tmp_config_dir
        fake_dir.mkdir(parents=True, exist_ok=True)
        fake_path.write_text("{ not valid json")

        rules = alerts_mod.load_rules()
        # Fallback para defaults
        assert len(rules) > 0

    def test_partial_rule_skipped(self, tmp_config_dir):
        """Rule com campos faltando eh ignorado, outros sao mantidos."""
        fake_dir, fake_path = tmp_config_dir
        fake_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "rules": [
                {"id": "ok", "metric": "cpu_pct", "threshold": 80.0},  # ok
                {"id": "broken"},  # missing fields
            ]
        }
        fake_path.write_text(json.dumps(data))

        rules = alerts_mod.load_rules()
        # Apenas o valido foi carregado
        assert len(rules) == 1
        assert rules[0].id == "ok"


class TestSaveRules:
    def test_creates_file(self, tmp_config_dir):
        fake_dir, fake_path = tmp_config_dir
        rule = AlertRule(
            id="test", metric="cpu_pct", threshold=80.0,
            op="gt", duration_sec=10, cooldown_sec=60,
            label="Test", enabled=True,
        )
        ok, err = alerts_mod.save_rules([rule])
        assert ok is True
        assert err == ""
        assert fake_path.exists()

    def test_roundtrip(self, tmp_config_dir):
        """Save → load deve retornar mesmas regras."""
        fake_dir, fake_path = tmp_config_dir
        original = [
            AlertRule(
                id="r1", metric="mem_pct", threshold=85.0,
                op="gt", duration_sec=20, cooldown_sec=300,
                label="MemHigh", enabled=True,
            ),
            AlertRule(
                id="r2", metric="cpu_temp_c", threshold=80.0,
                op="gt", duration_sec=5, cooldown_sec=60,
                label="TempHigh", enabled=False,
            ),
        ]
        alerts_mod.save_rules(original)
        loaded = alerts_mod.load_rules()

        assert len(loaded) == 2
        # Compara por dict pra evitar problemas de identidade
        original_dicts = [{"id": r.id, "metric": r.metric, "threshold": r.threshold} for r in original]
        loaded_dicts = [{"id": r.id, "metric": r.metric, "threshold": r.threshold} for r in loaded]
        assert original_dicts == loaded_dicts

    def test_permissions_0600(self, tmp_config_dir):
        """LGPD: arquivo deve ter mode 0600."""
        fake_dir, fake_path = tmp_config_dir
        rule = AlertRule(
            id="t", metric="cpu_pct", threshold=80.0,
            op="gt", duration_sec=5, cooldown_sec=60,
        )
        alerts_mod.save_rules([rule])

        mode = stat.S_IMODE(fake_path.stat().st_mode)
        assert mode == 0o600

    def test_empty_list_saves_empty(self, tmp_config_dir):
        fake_dir, fake_path = tmp_config_dir
        ok, err = alerts_mod.save_rules([])
        assert ok is True
        data = json.loads(fake_path.read_text())
        assert data == {"rules": []}


class TestDefaultRules:
    def test_default_rules_are_opt_in(self):
        """Todas regras default devem estar enabled=False."""
        rules = alerts_mod._default_rules()
        for rule in rules:
            assert rule.enabled is False, f"Default rule {rule.id} esta enabled=True"

    def test_default_rules_have_unique_ids(self):
        rules = alerts_mod._default_rules()
        ids = [r.id for r in rules]
        assert len(ids) == len(set(ids))

    def test_default_rules_metrics_existem(self):
        """Cada default rule.metric deve estar em METRICS."""
        rules = alerts_mod._default_rules()
        for rule in rules:
            assert rule.metric in alerts_mod.METRICS, (
                f"Rule {rule.id} usa metrica desconhecida: {rule.metric}"
            )
