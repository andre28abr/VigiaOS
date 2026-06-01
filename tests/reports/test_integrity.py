"""Testes do selo de integridade (SHA-256) + pacote de auditoria (.zip)."""

from __future__ import annotations

import hashlib
import re
import zipfile
from datetime import datetime

from vigia_reports import backend, renderer


class TestDocSeal:
    def test_deterministic(self):
        ctx = {"a": 1, "b": [1, 2], "meta": {"generated_at": "t"}}
        assert renderer._doc_seal(ctx) == renderer._doc_seal(dict(ctx))

    def test_changes_with_content(self):
        assert renderer._doc_seal({"x": 1}) != renderer._doc_seal({"x": 2})

    def test_is_hex_sha256(self):
        s = renderer._doc_seal({"x": 1})
        assert len(s) == 64 and all(c in "0123456789abcdef" for c in s)

    def test_handles_non_serializable(self):
        s = renderer._doc_seal({"d": datetime(2026, 5, 31), "o": object()})
        assert len(s) == 64


class TestWriteReportSidecar:
    def test_sidecar_matches_file(self, tmp_path):
        html = "<html><body>olá, mundo</body></html>"
        path = renderer.write_report(html, "activity_overview", tmp_path)
        sidecar = path.with_name(path.name + ".sha256")
        assert sidecar.is_file()
        digest, _, fname = sidecar.read_text().partition("  ")
        assert fname.strip() == path.name
        # bate com o sha256 do arquivo → `sha256sum -c` funcionaria
        assert digest.strip() == hashlib.sha256(path.read_bytes()).hexdigest()


class TestSealInRender:
    def test_seal_and_recipe_in_footer(self):
        data = {
            "period": backend.Period(since=datetime(2026, 5, 24), until=datetime(2026, 5, 31)),
            "elevated_mode": True,
            "status": {"level": "ok", "label": "x"},
            "summary": "s",
            "score": {"ok": 1, "total": 1, "pct": 100, "unknown": 0},
            "checks": [{"label": "Firewall", "state": "ok", "value": "ativo",
                        "detail": "d", "critical": True}],
        }
        html = renderer.render_html("lgpd_compliance", data)
        assert "Selo de integridade" in html
        assert "sha256sum -c" in html
        assert re.search(r"[0-9a-f]{64}", html)  # o hash aparece


class TestAuditPackage:
    def test_empty_dir_errors(self, tmp_path):
        zp, n, err = renderer.build_audit_package(tmp_path)
        assert zp is None and n == 0 and err

    def test_packages_reports_and_sidecars(self, tmp_path):
        renderer.write_report("<html>1</html>", "activity_overview", tmp_path)
        renderer.write_report("<html>2</html>", "auth_events", tmp_path)
        zp, n, err = renderer.build_audit_package(tmp_path)
        assert err == "" and n == 2 and zp is not None and zp.is_file()
        with zipfile.ZipFile(zp) as zf:
            names = zf.namelist()
        assert len([x for x in names if x.endswith(".html")]) == 2
        assert len([x for x in names if x.endswith(".html.sha256")]) == 2
        assert "MANIFEST.txt" in names
        assert "LEIA-ME.txt" in names

    def test_sidecar_in_zip_verifies(self, tmp_path):
        path = renderer.write_report("<html>conteudo</html>", "activity_overview", tmp_path)
        zp, _, _ = renderer.build_audit_package(tmp_path)
        with zipfile.ZipFile(zp) as zf:
            html_bytes = zf.read(path.name)
            sidecar_txt = zf.read(path.name + ".sha256").decode()
        assert sidecar_txt.split()[0] == hashlib.sha256(html_bytes).hexdigest()

    def test_manifest_lists_hashes(self, tmp_path):
        renderer.write_report("<html>x</html>", "activity_overview", tmp_path)
        zp, _, _ = renderer.build_audit_package(tmp_path)
        with zipfile.ZipFile(zp) as zf:
            manifest = zf.read("MANIFEST.txt").decode()
        assert "PACOTE DE AUDITORIA" in manifest
        assert re.search(r"[0-9a-f]{64}", manifest)
