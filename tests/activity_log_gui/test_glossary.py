"""Testes do glossário do Activity Log (rótulos PT-BR + explain) — puro."""

from __future__ import annotations

from vigia_log_gui.glossary import (
    SOURCES_INFO,
    Explanation,
    explain,
    severity_label,
    severity_short,
    source_label,
)


def test_severity_labels_ptbr():
    assert severity_label("suspicious") == "Atenção"
    assert severity_label("interesting") == "Vale olhar"
    assert severity_label("routine") == "Rotina"
    assert severity_short("suspicious") == "atenção"


def test_source_labels_ptbr_handle_journal_and_journald():
    assert source_label("audit") == "Auditoria de segurança"
    assert source_label("journald") == "Diário do sistema"
    assert source_label("journal") == "Diário do sistema"
    assert source_label("fail2ban") == "Bloqueios de IP"


def test_unknown_label_falls_back_to_code():
    assert source_label("xyz") == "xyz"
    assert severity_label("xyz") == "xyz"


def test_explain_fail2ban_ban():
    e = explain("fail2ban", "IP 1.2.3.4 banido após 3 tentativas SSH")
    assert isinstance(e, Explanation)
    assert e.title == "IP bloqueado"
    assert e.what and e.normal and e.action


def test_explain_failed_login():
    e = explain("journal", "Falha de senha para root via SSH")
    assert "login" in e.title.lower()


def test_explain_sudo():
    e = explain("audit", "usuario executou sudo dnf install")
    assert "administrador" in e.title.lower()


def test_explain_fallback_by_source():
    e = explain("audit", "mensagem totalmente genérica zzz")
    assert e.title == "Evento de auditoria"


def test_explain_generic_for_unknown_source():
    e = explain("desconhecido", "evento qualquer")
    assert isinstance(e, Explanation)
    assert e.title == "Evento do sistema"


def test_explain_never_crashes_on_empty():
    e = explain("", "")
    assert isinstance(e, Explanation)
    assert e.title


def test_sources_info_covers_the_three_logs():
    assert {s.code for s in SOURCES_INFO} == {"journald", "audit", "fail2ban"}
    for s in SOURCES_INFO:
        assert s.label and s.what and s.when and s.icon
