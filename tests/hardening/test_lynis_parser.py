"""Testes do parser do report Lynis (vigia_hardening.backend).

Lynis grava /var/log/lynis-report.dat em formato chave=valor, com algumas
chaves repetidas viram listas (warning[], suggestion[], control[]). Aqui
exercitamos parse_report() com um report realista + os helpers puros
(_parse_finding, _parse_datetime, category_label, format_age).

Nao precisa de Lynis instalado nem de root — alimentamos um .dat de tmp_path.
"""

from __future__ import annotations

from datetime import datetime

from vigia_hardening import backend


SAMPLE_REPORT = """# Lynis Report
lynis_version=3.0.9
hardening_index=67
auditor=vigia-hardening
finish=true
report_datetime_start=2026-05-13 12:30:00
report_datetime_end=2026-05-13 12:34:56
tests_executed=BOOT-5104|KRNL-5677|KRNL-5820|SSH-7408|
tests_skipped=PHP-2211|
warning[]=SSH-7408|Consider hardening SSH configuration|-|-
warning[]=KRNL-5820|/dev/null permissions|text:detail aqui|-
suggestion[]=BOOT-5104|Add a password to GRUB|-|-
suggestion[]=KRNL-5677|Check sysctl values|-|-
suggestion[]=AUTH-9286|Configure password aging|-|-
plugin_enabled[]=pam
control[]=CUST-0001:OK
control[]=CUST-0002:FAILED
exception_event[]=alguma excecao
# linha de comentario ignorada
linha_sem_igual
chave_vazia=
"""


def _write(tmp_path, text: str):
    p = tmp_path / "lynis-report.dat"
    p.write_text(text, encoding="utf-8")
    return p


class TestParseReportScalars:
    def test_scalar_fields(self, tmp_path):
        rep = backend.parse_report(_write(tmp_path, SAMPLE_REPORT))
        assert rep.hardening_index == 67
        assert rep.auditor == "vigia-hardening"
        assert rep.finish is True
        assert rep.has_data() is True

    def test_tests_executed_counts_ids(self, tmp_path):
        rep = backend.parse_report(_write(tmp_path, SAMPLE_REPORT))
        # 4 ids nao-vazios (o '|' final nao conta)
        assert rep.tests_executed == 4
        assert rep.tests_skipped == 1

    def test_datetimes_parsed(self, tmp_path):
        rep = backend.parse_report(_write(tmp_path, SAMPLE_REPORT))
        assert rep.started_at == datetime(2026, 5, 13, 12, 30, 0)
        assert rep.finished_at == datetime(2026, 5, 13, 12, 34, 56)


class TestParseReportLists:
    def test_warnings(self, tmp_path):
        rep = backend.parse_report(_write(tmp_path, SAMPLE_REPORT))
        assert len(rep.warnings) == 2
        w0 = rep.warnings[0]
        assert w0.test_id == "SSH-7408"
        assert w0.category == "SSH"
        assert w0.message == "Consider hardening SSH configuration"
        assert w0.details == ""  # ambos campos eram '-'
        # detalhe preservado quando nao e' '-'
        assert rep.warnings[1].details == "text:detail aqui"

    def test_suggestions(self, tmp_path):
        rep = backend.parse_report(_write(tmp_path, SAMPLE_REPORT))
        assert len(rep.suggestions) == 3
        cats = {s.category for s in rep.suggestions}
        assert cats == {"BOOT", "KRNL", "AUTH"}

    def test_controls_split_by_status(self, tmp_path):
        rep = backend.parse_report(_write(tmp_path, SAMPLE_REPORT))
        assert rep.controls_passed == ["CUST-0001"]
        assert rep.controls_failed == ["CUST-0002"]

    def test_plugins_and_exceptions(self, tmp_path):
        rep = backend.parse_report(_write(tmp_path, SAMPLE_REPORT))
        assert rep.plugins == ["pam"]
        assert rep.exceptions == ["alguma excecao"]

    def test_categories_summary(self, tmp_path):
        rep = backend.parse_report(_write(tmp_path, SAMPLE_REPORT))
        summ = rep.categories_summary()
        assert summ["SSH"] == {"warnings": 1, "suggestions": 0}
        assert summ["KRNL"] == {"warnings": 1, "suggestions": 1}
        assert summ["BOOT"] == {"warnings": 0, "suggestions": 1}
        assert summ["AUTH"] == {"warnings": 0, "suggestions": 1}


class TestParseReportEdgeCases:
    def test_missing_file_returns_empty(self, tmp_path):
        rep = backend.parse_report(tmp_path / "nao-existe.dat")
        assert rep.hardening_index is None
        assert rep.tests_executed == 0
        assert rep.warnings == []
        assert rep.has_data() is False

    def test_ignores_comments_and_malformed_lines(self, tmp_path):
        rep = backend.parse_report(
            _write(tmp_path, "# so comentario\nlixo sem igual\nchave_vazia=\n")
        )
        assert rep.has_data() is False
        assert rep.warnings == []

    def test_invalid_hardening_index_ignored(self, tmp_path):
        rep = backend.parse_report(_write(tmp_path, "hardening_index=nan\n"))
        assert rep.hardening_index is None

    def test_finish_false_when_not_true(self, tmp_path):
        rep = backend.parse_report(_write(tmp_path, "finish=false\n"))
        assert rep.finish is False


class TestParseFinding:
    def test_full_pipe_form(self):
        f = backend._parse_finding("KRNL-5820|mensagem|-|-")
        assert f.test_id == "KRNL-5820"
        assert f.category == "KRNL"
        assert f.message == "mensagem"
        assert f.details == ""

    def test_details_join_non_dash(self):
        f = backend._parse_finding("FILE-1234|msg|detalhe um|detalhe dois")
        assert f.details == "detalhe um|detalhe dois"

    def test_id_without_dash_is_other(self):
        f = backend._parse_finding("SEMCATEGORIA|msg")
        assert f.category == "OTHER"

    def test_empty_value(self):
        f = backend._parse_finding("")
        assert f.test_id == ""
        assert f.category == "OTHER"


class TestParseDatetime:
    def test_valid(self):
        assert backend._parse_datetime("2026-01-02 03:04:05") == datetime(
            2026, 1, 2, 3, 4, 5
        )

    def test_whitespace_tolerant(self):
        assert backend._parse_datetime("  2026-01-02 03:04:05  ") == datetime(
            2026, 1, 2, 3, 4, 5
        )

    def test_invalid_returns_none(self):
        assert backend._parse_datetime("ontem a tarde") is None
        assert backend._parse_datetime("") is None


class TestCategoryLabel:
    def test_known(self):
        assert backend.category_label("KRNL") == "Kernel e sysctl"
        assert backend.category_label("SSH") == "Servidor SSH"

    def test_case_insensitive(self):
        assert backend.category_label("krnl") == "Kernel e sysctl"

    def test_unknown_falls_back_to_code(self):
        assert backend.category_label("ZZZZ") == "ZZZZ"


class TestFormatAge:
    def test_none(self):
        assert backend.format_age(None) == "Nunca executado"

    def test_now(self):
        assert backend.format_age(0) == "agora mesmo"

    def test_minutes(self):
        assert backend.format_age(42) == "ha 42 min"

    def test_hours(self):
        assert backend.format_age(150) == "ha 2h"

    def test_days_plural(self):
        assert backend.format_age(60 * 24 * 3) == "ha 3 dias"

    def test_one_day_singular(self):
        assert backend.format_age(60 * 24) == "ha 1 dia"
