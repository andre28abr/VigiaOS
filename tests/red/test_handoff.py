"""Teste do handoff — passagem de alvo Recon → Network Scanner (em memória)."""

from __future__ import annotations

from vigia_red import handoff


def test_set_peek_take():
    handoff.set_scan_target("1.2.3.4")
    assert handoff.peek() == "1.2.3.4"
    assert handoff.take_scan_target() == "1.2.3.4"
    assert handoff.take_scan_target() == ""   # consumo único


def test_strip():
    handoff.set_scan_target("  9.9.9.9  ")
    assert handoff.take_scan_target() == "9.9.9.9"


def test_vazio():
    handoff.set_scan_target("")
    assert handoff.take_scan_target() == ""
