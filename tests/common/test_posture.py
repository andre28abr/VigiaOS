"""Testes da camada de postura (avaliadores puros + overall) — sem GTK."""

from __future__ import annotations

from vigia_common import posture as p
from vigia_common.posture import BAD, OK, UNKNOWN, WARN, Check


# --------------------------------------------------------------------------- #
# Firewall
# --------------------------------------------------------------------------- #

def test_firewall_active_ok():
    c = p.eval_firewall(True)
    assert c.status == OK and c.key == "firewall" and not c.fix_tool


def test_firewall_inactive_bad_with_fix():
    c = p.eval_firewall(False)
    assert c.status == BAD
    assert c.fix_tool == "firewall-gui" and c.fix_label


def test_firewall_unknown():
    assert p.eval_firewall(None).status == UNKNOWN


# --------------------------------------------------------------------------- #
# Updates
# --------------------------------------------------------------------------- #

def test_updates_none_pending_ok():
    assert p.eval_updates(0).status == OK


def test_updates_pending_warn_and_plural():
    one = p.eval_updates(1)
    assert one.status == WARN and "disponível" in one.detail
    many = p.eval_updates(5)
    assert "5 atualizações" in many.detail


def test_updates_unknown():
    assert p.eval_updates(None).status == UNKNOWN


# --------------------------------------------------------------------------- #
# Antivírus
# --------------------------------------------------------------------------- #

def test_av_not_installed_warn():
    assert p.eval_antivirus(False, None).status == WARN


def test_av_fresh_db_ok():
    assert p.eval_antivirus(True, 2.0).status == OK
    assert p.eval_antivirus(True, 7.0).status == OK


def test_av_stale_db_warn():
    c = p.eval_antivirus(True, 30.0)
    assert c.status == WARN and "30 dias" in c.detail


def test_av_missing_db_warn():
    assert p.eval_antivirus(True, None).status == WARN


# --------------------------------------------------------------------------- #
# Privacidade
# --------------------------------------------------------------------------- #

def test_privacy_all_hardened_ok():
    assert p.eval_privacy(4, 4).status == OK


def test_privacy_partial_warn():
    c = p.eval_privacy(2, 4)
    assert c.status == WARN and "2" in c.detail


def test_privacy_none_checkable_unknown():
    assert p.eval_privacy(0, 0).status == UNKNOWN


# --------------------------------------------------------------------------- #
# Overall (pior status vence)
# --------------------------------------------------------------------------- #

def test_overall_all_ok():
    checks = [Check("a", "A", OK, ""), Check("b", "B", OK, "")]
    assert p.overall_status(checks) == OK


def test_overall_bad_beats_warn():
    checks = [Check("a", "A", OK, ""), Check("b", "B", WARN, ""),
              Check("c", "C", BAD, "")]
    assert p.overall_status(checks) == BAD


def test_overall_warn_beats_unknown_and_ok():
    checks = [Check("a", "A", OK, ""), Check("b", "B", UNKNOWN, ""),
              Check("c", "C", WARN, "")]
    assert p.overall_status(checks) == WARN


def test_overall_empty_is_ok():
    assert p.overall_status([]) == OK
