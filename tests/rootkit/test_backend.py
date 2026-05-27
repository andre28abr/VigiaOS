"""Tests pro backend do Vigia Rootkit Scanner.

Cobre:
- dnscrypt_installed/rkhunter_installed detection via shutil.which
- Parser de output do chkrootkit (linhas reais)
- Parser de output do rkhunter (linhas reais)
- Dataclasses Versions/ScanResult/Finding defaults
- list_recent_reports / load_report (JSON I/O)
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from vigia_rootkit import backend


# ============================================================
# Sanity
# ============================================================


class TestInstalledChecks:
    @patch("vigia_rootkit.backend.shutil.which")
    def test_chkrootkit_installed_true(self, mock_which):
        mock_which.return_value = "/usr/sbin/chkrootkit"
        assert backend.chkrootkit_installed() is True

    @patch("vigia_rootkit.backend.shutil.which")
    def test_chkrootkit_installed_false(self, mock_which):
        mock_which.return_value = None
        assert backend.chkrootkit_installed() is False

    @patch("vigia_rootkit.backend.shutil.which")
    def test_rkhunter_installed_true(self, mock_which):
        mock_which.return_value = "/usr/bin/rkhunter"
        assert backend.rkhunter_installed() is True

    @patch("vigia_rootkit.backend.shutil.which")
    def test_rkhunter_installed_false(self, mock_which):
        mock_which.return_value = None
        assert backend.rkhunter_installed() is False


# ============================================================
# Parser chkrootkit
# ============================================================


class TestChkrootkitParser:
    """Linhas reais do chkrootkit (versao 0.58b)."""

    def test_clean_line_returns_none(self):
        # Linhas OK nao devem virar findings
        for line in [
            "Checking `aliens'... no suspect files",
            "Checking `asp'... not infected",
            "Checking `bindshell'... not infected",
            "Checking `lkm'... nothing detected",
            "Checking `ifpromisc'... not infected",
            "Checking `chkutmp'... The tty of the following user process(es) were not found",
            "ROOTDIR is `/'",
            "",
            "/usr/lib/python3.13: nothing detected",
        ]:
            f = backend._parse_chkrootkit_line(line)
            assert f is None, f"Esperava None pra: {line!r}, recebeu {f}"

    def test_infected_line_returns_finding(self):
        line = "Checking `bindshell'... INFECTED"
        f = backend._parse_chkrootkit_line(line)
        assert f is not None
        assert f.severity == "INFECTED"
        assert f.test == "bindshell"

    def test_warning_lkm_returns_finding(self):
        # Output real: "Checking `lkm'... You have    2 process hidden..."
        line = "Checking `lkm'... You have 2 process hidden for ps command"
        f = backend._parse_chkrootkit_line(line)
        assert f is not None
        assert f.severity == "WARNING"
        assert f.test == "lkm"

    def test_vulnerable_keyword_returns_warning(self):
        line = "Checking `kuang2'... vulnerable but disabled"
        f = backend._parse_chkrootkit_line(line)
        assert f is not None
        assert f.severity == "WARNING"

    def test_not_infected_passes(self):
        """'not infected' NAO eh problema."""
        line = "Checking `wted'... not infected"
        assert backend._parse_chkrootkit_line(line) is None


# ============================================================
# Parser rkhunter
# ============================================================


class TestRkhunterParser:
    """Linhas reais do rkhunter 1.4.6."""

    def test_ok_bracket_returns_none(self):
        for line in [
            "  Checking for prerequisites               [ OK ]",
            "  Checking for missing files               [ OK ]",
            "  Checking the system startup files          [ Found ]",
        ]:
            assert backend._parse_rkhunter_line(line) is None, \
                f"Esperava None pra: {line!r}"

    def test_warning_bracket(self):
        line = "  Checking SSH protocol v1 setting         [ Warning ]"
        f = backend._parse_rkhunter_line(line)
        assert f is not None
        assert f.severity == "WARNING"

    def test_warning_prefix_line(self):
        line = "Warning: The SSH and rkhunter configuration options should be the same"
        f = backend._parse_rkhunter_line(line)
        assert f is not None
        assert f.severity == "WARNING"
        assert "rkhunter-warning" in f.test

    def test_infected_bracket(self):
        line = "  Checking for Volc rootkit              [ Infected ]"
        f = backend._parse_rkhunter_line(line)
        assert f is not None
        assert f.severity == "INFECTED"

    def test_empty_line(self):
        assert backend._parse_rkhunter_line("") is None
        assert backend._parse_rkhunter_line("   ") is None

    def test_random_text_no_bracket(self):
        line = "Rootkit Hunter version 1.4.6 ( http://rkhunter.sourceforge.net )"
        assert backend._parse_rkhunter_line(line) is None


# ============================================================
# Dataclasses
# ============================================================


class TestDataclasses:
    def test_versions_defaults(self):
        v = backend.Versions()
        assert v.chkrootkit == ""
        assert v.rkhunter == ""

    def test_scan_result_defaults(self):
        r = backend.ScanResult(scanner="chkrootkit")
        assert r.scanner == "chkrootkit"
        assert r.findings == []
        assert r.tests_run == 0
        assert r.warnings_count == 0
        assert r.infected_count == 0
        assert r.elapsed_sec == 0.0
        assert r.cancelled is False
        assert r.error == ""

    def test_finding_required_fields(self):
        f = backend.Finding(
            test="aliens", severity="WARNING", detail="2 processes hidden",
        )
        assert f.test == "aliens"
        assert f.severity == "WARNING"
        assert f.detail == "2 processes hidden"
        assert f.line == ""  # default


# ============================================================
# Reports I/O
# ============================================================


class TestReports:
    def test_save_and_load_report(self, tmp_path, monkeypatch):
        monkeypatch.setattr(backend, "REPORTS_DIR", tmp_path)

        result = backend.ScanResult(
            scanner="chkrootkit",
            started_at="2026-05-27T15:00:00",
            tests_run=42,
            warnings_count=1,
            infected_count=0,
            elapsed_sec=12.3,
            raw_output="Checking aliens... ok\n",
        )
        result.findings.append(
            backend.Finding(test="lkm", severity="WARNING", detail="hidden processes"),
        )

        saved = backend._save_report(result)
        assert saved is not None
        assert saved.exists()

        # Permissoes 0600
        mode = saved.stat().st_mode & 0o777
        assert mode == 0o600, f"Esperava 0600, foi {oct(mode)}"

        # Carrega
        data = backend.load_report(str(saved))
        assert data is not None
        assert data["scanner"] == "chkrootkit"
        assert data["tests_run"] == 42
        assert data["warnings_count"] == 1
        assert len(data["findings"]) == 1
        assert data["findings"][0]["test"] == "lkm"

    def test_list_recent_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(backend, "REPORTS_DIR", tmp_path)
        assert backend.list_recent_reports() == []

    def test_list_recent_sorted_newest_first(self, tmp_path, monkeypatch):
        monkeypatch.setattr(backend, "REPORTS_DIR", tmp_path)

        # Cria 3 reports com timestamps diferentes
        import time as _t
        for i, name in enumerate(["a", "b", "c"]):
            f = tmp_path / f"chkrootkit-{name}.json"
            f.write_text(json.dumps({
                "scanner": "chkrootkit",
                "started_at": f"2026-05-27T15:00:0{i}",
                "tests_run": 0, "warnings_count": 0, "infected_count": 0,
                "elapsed_sec": 0, "cancelled": False, "error": "",
                "findings": [], "raw_output": "",
            }))
            _t.sleep(0.01)  # garantir mtime diferente

        reports = backend.list_recent_reports(limit=10)
        assert len(reports) == 3
        # Mais novo primeiro = "c" deve ser primeiro
        assert reports[0]["started_at"] == "2026-05-27T15:00:02"

    def test_load_report_missing_file(self):
        assert backend.load_report("/tmp/nao-existe-vigia-test.json") is None


# ============================================================
# Constantes documentadas
# ============================================================


class TestConstants:
    def test_reports_dir_under_share(self):
        assert "share/vigia-rootkit/scans" in str(backend.REPORTS_DIR)
