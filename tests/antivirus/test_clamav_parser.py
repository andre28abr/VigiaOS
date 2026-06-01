"""Testes dos parsers do ClamAV (vigia_antivirus.backend).

Cobre:
- get_db_info(): parse da linha `clamscan --version`
  ("ClamAV 1.0.5/27365/Mon May 13 ...")
- _extract_int / db_age_days (helpers puros)
- o parser de scan (linhas "<path>: <SIG> FOUND" + bloco SCAN SUMMARY),
  exercitado via scan_async com um Popen falso — sem clamscan real
- list_recent_reports(): leitura/ordenacao dos JSON salvos

Nao precisa de ClamAV instalado.
"""

from __future__ import annotations

import json
import os
import threading
import time

from vigia_antivirus import backend


# ============================================================
# Version string parser (get_db_info)
# ============================================================


def _mk_db(tmp_path, name="daily.cld", age_days=0):
    """Cria um dir de base com 1 arquivo de assinatura com mtime = age_days atras."""
    db = tmp_path / "clamav"
    db.mkdir(exist_ok=True)
    f = db / name
    f.write_bytes(b"x")
    ts = int(time.time()) - age_days * 86400
    os.utime(f, (ts, ts))
    return db, ts


class TestGetDbInfo:
    def test_versao_do_version_string_idade_do_mtime(self, monkeypatch, tmp_path):
        monkeypatch.setattr(backend, "clamav_installed", lambda: True)
        monkeypatch.setattr(
            backend, "_run",
            lambda cmd, timeout=10: (0, "ClamAV 1.4.4/27600/Sun Jun  1 03:30:00 2026\n", ""),
        )
        db, ts = _mk_db(tmp_path, age_days=2)
        info = backend.get_db_info(db_dirs=(str(db),))
        # engine + db version saem da string --version
        assert info.engine_version == "1.4.4"
        assert info.db_version == "27600"
        # idade vem do mtime do arquivo (nao da data da string)
        assert info.last_update_epoch == ts
        assert backend.db_age_days(info) == 2
        assert info.last_update  # string formatada nao-vazia

    def test_idade_independente_de_locale(self, monkeypatch, tmp_path):
        # REGRESSAO: antes a idade vinha de strptime("%a %b ...") na data do
        # --version, que falha sob locale pt-BR (espera "Dom"/"Jun", recebe o
        # ingles "Sun"/"Jun" do ClamAV) -> epoch 0 -> "idade desconhecida"
        # mesmo com a base recem-atualizada. Agora vem do mtime: imune a locale.
        monkeypatch.setattr(backend, "clamav_installed", lambda: True)
        monkeypatch.setattr(
            backend, "_run",
            # data em portugues / formato estranho: irrelevante agora
            lambda cmd, timeout=10: (0, "ClamAV 1.4.4/27600/Dom  1 Jun 2026\n", ""),
        )
        db, ts = _mk_db(tmp_path, name="main.cvd", age_days=0)
        info = backend.get_db_info(db_dirs=(str(db),))
        assert info.last_update_epoch > 0
        assert backend.db_age_days(info) == 0  # atualizada hoje -> sem banner

    def test_sem_arquivos_de_base_idade_desconhecida(self, monkeypatch, tmp_path):
        # Dir existe mas vazio -> idade desconhecida (banner correto: sem base).
        monkeypatch.setattr(backend, "clamav_installed", lambda: True)
        monkeypatch.setattr(backend, "_run", lambda cmd, timeout=10: (0, "ClamAV 1.4.4\n", ""))
        empty = tmp_path / "vazio"
        empty.mkdir()
        info = backend.get_db_info(db_dirs=(str(empty),))
        assert info.last_update_epoch == 0
        assert backend.db_age_days(info) is None

    def test_not_installed_returns_blank(self, monkeypatch):
        monkeypatch.setattr(backend, "clamav_installed", lambda: False)
        info = backend.get_db_info()
        assert info.engine_version == ""
        assert info.db_version == ""

    def test_malformed_version_line_is_safe(self, monkeypatch, tmp_path):
        monkeypatch.setattr(backend, "clamav_installed", lambda: True)
        monkeypatch.setattr(backend, "_run", lambda cmd, timeout=10: (0, "lixo\n", ""))
        info = backend.get_db_info(db_dirs=(str(tmp_path),))
        # sem '/' nem 'ClamAV X.Y' -> campos ficam vazios, sem crash
        assert info.engine_version == ""
        assert info.db_version == ""


class TestDbAgeDays:
    def test_three_days(self):
        info = backend.DbInfo(last_update_epoch=int(time.time()) - 3 * 86400)
        assert backend.db_age_days(info) == 3

    def test_unknown_when_no_epoch(self):
        assert backend.db_age_days(backend.DbInfo()) is None


class TestExtractInt:
    def test_pulls_first_int(self):
        assert backend._extract_int("Scanned files: 1234") == 1234

    def test_zero(self):
        assert backend._extract_int("Infected files: 0") == 0

    def test_no_digits(self):
        assert backend._extract_int("sem numeros aqui") == 0


# ============================================================
# Scan output parser (FOUND lines + SCAN SUMMARY) via Popen falso
# ============================================================


class _FakePopen:
    """Imita subprocess.Popen o suficiente pro worker do scan_async."""

    def __init__(self, lines, returncode):
        self.stdout = iter(lines)
        self.returncode = returncode

    def wait(self, timeout=None):
        return self.returncode

    def terminate(self):
        self.returncode = -15


SCAN_LINES = [
    "/home/user/eicar.txt: Eicar-Signature FOUND\n",
    "/home/user/clean.txt: OK\n",
    "/home/user/sub/virus.exe: Win.Test.EICAR_HDB-1 FOUND\n",
    "\n",
    "----------- SCAN SUMMARY -----------\n",
    "Known viruses: 8600000\n",
    "Engine version: 1.0.5\n",
    "Scanned directories: 2\n",
    "Scanned files: 3\n",
    "Infected files: 2\n",
    "Data scanned: 12.34 MB\n",
    "Data read: 6.17 MB (ratio 2.00:1)\n",
    "Time: 1.234 sec (0 m 1 s)\n",
]


def _run_scan(monkeypatch, tmp_path, lines, returncode=1):
    monkeypatch.setattr(backend, "clamav_installed", lambda: True)
    monkeypatch.setattr(backend, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(
        backend.subprocess, "Popen", lambda *a, **k: _FakePopen(lines, returncode)
    )
    box: dict = {}
    done = threading.Event()

    def on_done(res):
        box["res"] = res
        done.set()

    t = backend.scan_async(str(tmp_path), on_line=lambda ln: None, on_done=on_done)
    t.join(timeout=5)
    assert done.is_set(), "scan_async nao chamou on_done"
    return box["res"]


class TestScanParser:
    def test_findings(self, monkeypatch, tmp_path):
        res = _run_scan(monkeypatch, tmp_path, SCAN_LINES)
        assert res.error == ""
        assert len(res.findings) == 2
        assert res.findings[0].path == "/home/user/eicar.txt"
        assert res.findings[0].signature == "Eicar-Signature"
        assert res.findings[1].path == "/home/user/sub/virus.exe"
        assert res.findings[1].signature == "Win.Test.EICAR_HDB-1"

    def test_summary_numbers(self, monkeypatch, tmp_path):
        res = _run_scan(monkeypatch, tmp_path, SCAN_LINES)
        assert res.scanned_dirs == 2
        assert res.scanned_files == 3
        assert res.infected_files == 2
        assert res.data_scanned == "12.34 MB"

    def test_clean_scan_no_findings(self, monkeypatch, tmp_path):
        lines = [
            "/home/user/a.txt: OK\n",
            "/home/user/b.txt: OK\n",
            "----------- SCAN SUMMARY -----------\n",
            "Scanned files: 2\n",
            "Infected files: 0\n",
        ]
        res = _run_scan(monkeypatch, tmp_path, lines, returncode=0)
        assert res.findings == []
        assert res.scanned_files == 2
        assert res.infected_files == 0
        assert res.error == ""

    def test_report_saved_with_findings(self, monkeypatch, tmp_path):
        res = _run_scan(monkeypatch, tmp_path, SCAN_LINES)
        reports = list((tmp_path / "reports").glob("scan-*.json"))
        assert len(reports) == 1
        data = json.loads(reports[0].read_text(encoding="utf-8"))
        assert len(data["findings"]) == 2
        assert data["infected_files"] == 2
        assert res.started_at  # ISO timestamp preenchido


# ============================================================
# list_recent_reports
# ============================================================


class TestListRecentReports:
    def test_filters_corrupt_and_orders_newest_first(self, monkeypatch, tmp_path):
        rd = tmp_path / "reports"
        rd.mkdir()
        monkeypatch.setattr(backend, "REPORTS_DIR", rd)
        base = time.time()
        for i in range(3):
            p = rd / f"scan-valid-{i}.json"
            p.write_text(json.dumps({"target": f"/t{i}"}), encoding="utf-8")
            os.utime(p, (base + 10 + i, base + 10 + i))  # i=2 e' o mais novo
        # corrompido e nao-dict ficam mais antigos -> nao tomam slot, e
        # mesmo lidos sao descartados
        bad = rd / "scan-bad.json"
        bad.write_text("{lixo", encoding="utf-8")
        os.utime(bad, (base, base))
        lst = rd / "scan-list.json"
        lst.write_text("[1, 2]", encoding="utf-8")
        os.utime(lst, (base + 1, base + 1))

        out = backend.list_recent_reports(limit=10)
        assert len(out) == 3
        assert all(isinstance(d, dict) for d in out)
        assert out[0]["target"] == "/t2"
        assert all("_file" in d for d in out)

    def test_missing_dir_returns_empty(self, monkeypatch, tmp_path):
        monkeypatch.setattr(backend, "REPORTS_DIR", tmp_path / "nao-existe")
        assert backend.list_recent_reports() == []
