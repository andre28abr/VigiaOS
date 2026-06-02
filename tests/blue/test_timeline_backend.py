"""Testes do backend do Vigia Timeline (cmd builders + parser psort json_line)."""

from __future__ import annotations

import json

from vigia_blue.modules.timeline import backend


# ============================================================
# Sanity / cmd builders
# ============================================================


def test_plaso_available(monkeypatch):
    def which(b):
        return "/usr/bin/" + b if b in ("log2timeline.py", "psort.py") else None
    monkeypatch.setattr(backend.shutil, "which", which)
    assert backend.plaso_available() is True
    assert backend.log2timeline_bin() == "log2timeline.py"
    assert backend.psort_bin() == "psort.py"


def test_plaso_absent(monkeypatch):
    monkeypatch.setattr(backend.shutil, "which", lambda _b: None)
    assert backend.plaso_available() is False


def test_build_log2timeline_cmd():
    cmd = backend.build_log2timeline_cmd("/t/x.plaso", "/data",
                                         bin_name="log2timeline.py")
    assert cmd == ["log2timeline.py", "--status_view", "none",
                   "/t/x.plaso", "/data"]
    assert isinstance(cmd, list)


def test_build_psort_cmd():
    cmd = backend.build_psort_cmd("/t/x.plaso", "/t/out.jsonl",
                                  bin_name="psort.py")
    assert cmd == ["psort.py", "-o", "json_line", "-w", "/t/out.jsonl",
                   "/t/x.plaso"]


# ============================================================
# _ts_from_micros
# ============================================================


def test_ts_from_micros_valid():
    # 1_700_000_000 s desde epoch ≈ 2023-11-14 (UTC)
    iso = backend._ts_from_micros(1_700_000_000_000_000)
    assert iso.startswith("2023-11-14")


def test_ts_from_micros_invalid():
    assert backend._ts_from_micros("xx") == ""
    assert backend._ts_from_micros(0) == ""
    assert backend._ts_from_micros(-5) == ""
    assert backend._ts_from_micros(None) == ""


# ============================================================
# parse_psort_jsonl
# ============================================================


def test_parse_uses_datetime_field():
    line = json.dumps({"datetime": "2026-06-01T10:00:00", "message": "abriu x",
                       "data_type": "fs:stat", "timestamp": 123})
    evs = backend.parse_psort_jsonl(line)
    assert len(evs) == 1
    assert evs[0].timestamp == "2026-06-01T10:00:00"
    assert evs[0].message == "abriu x" and evs[0].data_type == "fs:stat"


def test_parse_falls_back_to_micros():
    line = json.dumps({"timestamp": 1_700_000_000_000_000, "message": "y",
                       "data_type": "syslog:line", "parser": "syslog"})
    evs = backend.parse_psort_jsonl(line)
    assert evs[0].timestamp.startswith("2023-11-14")
    assert evs[0].source == "syslog"


def test_parse_skips_garbage_and_empty():
    text = "\n".join(["não json", "", json.dumps({"message": "ok"}), "[1,2]"])
    evs = backend.parse_psort_jsonl(text)
    assert len(evs) == 1 and evs[0].message == "ok"


def test_parse_max_events():
    text = "\n".join(json.dumps({"message": str(i)}) for i in range(10))
    evs = backend.parse_psort_jsonl(text, max_events=3)
    assert len(evs) == 3


def test_parse_empty():
    assert backend.parse_psort_jsonl("") == []
    assert backend.parse_psort_jsonl(None) == []


# ============================================================
# analyze_psort_file
# ============================================================


def test_analyze_psort_file_missing(tmp_path):
    res = backend.analyze_psort_file(tmp_path / "nao_existe.jsonl")
    assert res.error and res.events == []


def test_analyze_psort_file_ok(tmp_path):
    f = tmp_path / "tl.jsonl"
    f.write_text("\n".join([
        json.dumps({"datetime": "2026-06-01T09:00:00", "message": "a",
                    "data_type": "fs:stat"}),
        json.dumps({"datetime": "2026-06-01T09:01:00", "message": "b",
                    "data_type": "syslog:line"}),
    ]))
    res = backend.analyze_psort_file(f)
    assert res.total == 2 and len(res.events) == 2
    assert res.events[0].message == "a"
