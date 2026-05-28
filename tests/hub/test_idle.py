"""Tests pro IdleMonitor do Vigia Hub.

Como IdleMonitor depende de GTK4 widgets (EventControllerMotion,
EventControllerKey), so testa interface sem rodar GTK. Os fluxos
GTK-dependent sao testados manualmente via VM.
"""

from __future__ import annotations

from vigia_hub import idle


class TestIdleMonitorInit:
    def test_init_with_zero_minutes_clamps_to_one(self):
        """Mesmo se user pedir 0 min, monitor usa min 60s pra evitar bug."""
        mon = idle.IdleMonitor(window=None, timeout_minutes=0, on_idle=lambda: None)
        # 60 segundos (minimum) — evita 0s que causaria trigger imediato
        assert mon._timeout_sec >= 60

    def test_init_with_valid_minutes(self):
        mon = idle.IdleMonitor(window=None, timeout_minutes=10, on_idle=lambda: None)
        assert mon._timeout_sec == 600

    def test_init_stores_callback(self):
        cb = lambda: None  # noqa: E731
        mon = idle.IdleMonitor(window=None, timeout_minutes=5, on_idle=cb)
        assert mon._on_idle is cb


class TestIdleMonitorStop:
    def test_stop_is_idempotent(self):
        """Chamar stop() varias vezes nao crasha."""
        mon = idle.IdleMonitor(window=None, timeout_minutes=5, on_idle=lambda: None)
        mon.stop()
        mon.stop()  # nao deve crashar


class TestIdleMonitorReset:
    def test_reset_updates_last_activity(self):
        import time
        mon = idle.IdleMonitor(window=None, timeout_minutes=5, on_idle=lambda: None)
        before = mon._last_activity
        time.sleep(0.01)
        mon.reset()
        assert mon._last_activity > before
        assert mon._triggered is False


class TestConstants:
    def test_check_interval_reasonable(self):
        """Tick de 30s e' razoavel pra nao spam de timer."""
        assert idle.CHECK_INTERVAL_SEC == 30
