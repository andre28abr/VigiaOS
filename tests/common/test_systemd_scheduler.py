"""Testes do gerador de units systemd (conteúdo puro) — sem tocar no systemd."""

from __future__ import annotations

from vigia_common import scheduler


def test_service_unit_content():
    s = scheduler.service_unit("Varredura", "%h/.local/bin/vigia-scan")
    assert "[Service]" in s
    assert "Type=oneshot" in s
    assert "ExecStart=%h/.local/bin/vigia-scan" in s
    assert "Description=Varredura" in s


def test_timer_unit_content():
    t = scheduler.timer_unit("Varredura", "weekly")
    assert "[Timer]" in t
    assert "OnCalendar=weekly" in t
    assert "Persistent=true" in t
    assert "WantedBy=timers.target" in t
