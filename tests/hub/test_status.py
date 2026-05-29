"""Tests pro modulo status.py do Vigia Hub.

Cobre:
- humanize_age (varias faixas) + _iso_to_epoch
- last_antivirus_scan / last_rootkit_scan (parsing de relatorios)
- gather() smoke (com dirs isolados)
- tray_tooltip / format_text / to_dict
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from vigia_hub import backup, settings, status


# ============================================================
# humanize_age
# ============================================================


class TestHumanizeAge:
    def test_zero_is_unknown(self):
        assert status.humanize_age(0) == "desconhecido"

    def test_recent_is_now(self):
        now = time.time()
        assert status.humanize_age(now - 5, now=now) == "agora mesmo"

    def test_minutes(self):
        now = time.time()
        assert status.humanize_age(now - 300, now=now) == "há 5 min"

    def test_hours(self):
        now = time.time()
        assert status.humanize_age(now - 7200, now=now) == "há 2 h"

    def test_one_day_singular(self):
        now = time.time()
        assert status.humanize_age(now - 86400, now=now) == "há 1 dia"

    def test_multiple_days_plural(self):
        now = time.time()
        assert status.humanize_age(now - 3 * 86400, now=now) == "há 3 dias"

    def test_weeks(self):
        now = time.time()
        assert status.humanize_age(now - 14 * 86400, now=now) == "há 2 semanas"

    def test_future_clamped(self):
        now = time.time()
        # epoch no futuro -> nao explode, vira "agora mesmo"
        assert status.humanize_age(now + 999, now=now) == "agora mesmo"


class TestIsoToEpoch:
    def test_valid_iso(self):
        iso = "2026-05-28T12:00:00"
        assert status._iso_to_epoch(iso) > 0

    def test_invalid_returns_zero(self):
        assert status._iso_to_epoch("garbage") == 0.0
        assert status._iso_to_epoch("") == 0.0


class TestSafeInt:
    def test_valid_int(self):
        assert status._safe_int(5) == 5

    def test_numeric_string(self):
        assert status._safe_int("7") == 7

    def test_none_returns_default(self):
        assert status._safe_int(None) == 0

    def test_garbage_string_returns_default(self):
        assert status._safe_int("erro") == 0

    def test_list_returns_default(self):
        assert status._safe_int([1, 2]) == 0

    def test_dict_returns_default(self):
        assert status._safe_int({"x": 1}) == 0

    def test_custom_default(self):
        assert status._safe_int("x", default=-1) == -1


# ============================================================
# last scans
# ============================================================


@pytest.fixture
def scan_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    av = tmp_path / "av"
    rk = tmp_path / "rk"
    av.mkdir()
    rk.mkdir()
    monkeypatch.setattr(status, "AV_REPORTS_DIR", av)
    monkeypatch.setattr(status, "RK_REPORTS_DIR", rk)
    return av, rk


class TestLastAntivirusScan:
    def test_none_when_empty(self, scan_dirs):
        assert status.last_antivirus_scan() is None

    def test_clean_scan(self, scan_dirs):
        av, _ = scan_dirs
        (av / "scan-1.json").write_text(json.dumps({
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "infected_files": 0,
            "scanned_files": 1234,
        }))
        info = status.last_antivirus_scan()
        assert info is not None
        assert info.clean is True
        assert "limpo" in info.detail
        assert "1234" in info.detail

    def test_infected_scan(self, scan_dirs):
        av, _ = scan_dirs
        (av / "scan-1.json").write_text(json.dumps({
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "infected_files": 2,
            "scanned_files": 10,
        }))
        info = status.last_antivirus_scan()
        assert info is not None
        assert info.clean is False
        assert "2 ameaças" in info.detail

    def test_picks_newest(self, scan_dirs):
        av, _ = scan_dirs
        old = av / "scan-old.json"
        old.write_text(json.dumps({"infected_files": 9, "scanned_files": 1,
                                    "started_at": "2020-01-01T00:00:00"}))
        new = av / "scan-new.json"
        new.write_text(json.dumps({"infected_files": 0, "scanned_files": 5,
                                   "started_at": datetime.now().isoformat()}))
        # garante mtime mais novo no 'new'
        import os
        os.utime(old, (1, 1))
        info = status.last_antivirus_scan()
        assert info.clean is True  # pegou o novo (limpo)

    def test_malformed_int_fields_dont_crash(self, scan_dirs):
        """Relatorio corrompido (tipo errado) nao pode derrubar gather()."""
        av, _ = scan_dirs
        (av / "scan-1.json").write_text(json.dumps({
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "infected_files": "muitos",    # string nao-numerica
            "scanned_files": [1, 2, 3],     # lista
        }))
        info = status.last_antivirus_scan()  # nao deve levantar
        assert info is not None
        assert info.clean is True  # infected coerce -> 0


class TestLastRootkitScan:
    def test_none_when_empty(self, scan_dirs):
        assert status.last_rootkit_scan() is None

    def test_warnings(self, scan_dirs):
        _, rk = scan_dirs
        (rk / "rkhunter-1.json").write_text(json.dumps({
            "scanner": "rkhunter",
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "infected_count": 0,
            "warnings_count": 3,
        }))
        info = status.last_rootkit_scan()
        assert info is not None
        assert info.clean is False
        assert "3 alertas" in info.detail
        assert info.kind == "rootkit:rkhunter"

    def test_clean(self, scan_dirs):
        _, rk = scan_dirs
        (rk / "chkrootkit-1.json").write_text(json.dumps({
            "scanner": "chkrootkit",
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "infected_count": 0,
            "warnings_count": 0,
        }))
        info = status.last_rootkit_scan()
        assert info.clean is True
        assert info.detail == "limpo"

    def test_malformed_int_fields_dont_crash(self, scan_dirs):
        """Relatorio corrompido (tipo errado) nao pode derrubar gather()."""
        _, rk = scan_dirs
        (rk / "rkhunter-1.json").write_text(json.dumps({
            "scanner": "rkhunter",
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "infected_count": {"x": 1},    # dict
            "warnings_count": None,         # null
        }))
        info = status.last_rootkit_scan()  # nao deve levantar
        assert info is not None
        assert info.clean is True


# ============================================================
# gather + renderizacao
# ============================================================


@pytest.fixture
def isolated_gather(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Isola settings, dirs de scan e backups."""
    monkeypatch.setattr(status, "load_settings", lambda: settings.Settings())
    monkeypatch.setattr(status, "AV_REPORTS_DIR", tmp_path / "noav")
    monkeypatch.setattr(status, "RK_REPORTS_DIR", tmp_path / "nork")
    monkeypatch.setattr(backup, "BACKUP_DIR", tmp_path / "nobackups")


class TestGather:
    def test_returns_suite_status(self, isolated_gather):
        st = status.gather()
        assert isinstance(st, status.SuiteStatus)
        assert st.version  # nao vazio

    def test_tools_total_matches_registry(self, isolated_gather):
        from vigia_hub.registry import TOOLS
        st = status.gather()
        assert st.tools_total == len(TOOLS)
        assert st.tools_total > 0

    def test_key_binaries_present(self, isolated_gather):
        st = status.gather()
        names = {b.name for b in st.key_binaries}
        assert "clamscan" in names
        assert "rkhunter" in names

    def test_no_scans_when_dirs_empty(self, isolated_gather):
        st = status.gather()
        assert st.last_antivirus is None
        assert st.last_rootkit is None
        assert st.backups_count == 0


class TestRender:
    def test_tray_tooltip_is_str(self, isolated_gather):
        line = status.tray_tooltip()
        assert isinstance(line, str)
        assert line.startswith("Vigia Hub")
        assert "módulos" in line

    def test_format_text_contains_header(self, isolated_gather):
        text = status.format_text()
        assert "VigiaOS" in text
        assert "Módulos" in text

    def test_to_dict_is_json_serializable(self, isolated_gather):
        d = status.to_dict()
        # round-trip por JSON nao deve falhar
        s = json.dumps(d, ensure_ascii=False)
        assert "tools" in d
        assert d["tools_total"] == len(d["tools"])
        assert json.loads(s) == d
