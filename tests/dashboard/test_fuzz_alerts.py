"""Fuzz tests pro parser de regras de alerta do Dashboard (Etapa E)."""

from __future__ import annotations

from vigia_dashboard import alerts

FUZZ_JSON = [
    "", "   ", "lixo {{{", "{", "null", "42", "3.14", '"str"', "true",
    "[]", "[1, 2, 3]", "{}", '{"chave": "errada"}',
    '{"rules": "nao-lista"}', '{"rules": [1, 2, "x", null]}',
    '{"rules": [{"id": "x"}]}',                       # faltando metric/threshold
    '{"rules": [{"id": "x", "metric": "cpu", "threshold": "abc"}]}',  # threshold nao-numerico
    '{"rules": [{"id": "x", "metric": "cpu", "threshold": 90, "duration_sec": "NaN"}]}',
]


class TestLoadRulesFuzz:
    def test_never_crashes_returns_rules(self, tmp_path, monkeypatch):
        p = tmp_path / "alerts.json"
        monkeypatch.setattr(alerts, "CONFIG_PATH", p)
        for payload in FUZZ_JSON:
            p.write_text(payload, encoding="utf-8")
            out = alerts.load_rules()
            assert isinstance(out, list), f"payload quebrou: {payload!r}"
            assert all(isinstance(r, alerts.AlertRule) for r in out)
            # quando tudo invalido, cai nos defaults (nunca lista vazia)
            assert len(out) >= 1

    def test_valid_rule_parsed(self, tmp_path, monkeypatch):
        p = tmp_path / "alerts.json"
        monkeypatch.setattr(alerts, "CONFIG_PATH", p)
        p.write_text(
            '{"rules": [{"id": "r1", "metric": "cpu_percent", "threshold": 80}]}',
            encoding="utf-8",
        )
        out = alerts.load_rules()
        assert any(r.id == "r1" and r.threshold == 80.0 for r in out)
