"""Testes do gerador de relatório HTML (vigia_hub.reports_html). Puro, sem GTK."""

from __future__ import annotations

import re
from datetime import datetime

from vigia_common.events import Event
from vigia_hub import reports_html as rh


def _ev(**kw) -> Event:
    base = dict(id=1, ts="2026-01-01T10:00:00", ts_epoch=0.0, source="vuln",
                category="finding", severity="info", title="t", detail="", ref="")
    base.update(kw)
    return Event(**base)


class TestLabels:
    def test_sev(self):
        assert rh.sev_label("critical") == ("Crítico", "error")
        assert rh.sev_label("medium") == ("Médio", "warning")
        assert rh.sev_label("xyz") == ("Outro", "dim-label")

    def test_src(self):
        assert rh.src_label("antivirus") == "Antivírus"
        assert rh.src_label("desconhecido") == "desconhecido"


class TestBuildHtml:
    def test_estrutura(self):
        summary = {"total": 2, "by_severity": {"critical": 1, "info": 1},
                   "by_source": {"vuln": 2}}
        evs = [_ev(severity="critical", title="CVE-X", ref="https://a"),
               _ev(severity="info", title="tech-detect")]
        html = rh.build_html("Últimos 30 dias", summary, evs,
                             generated=datetime(2026, 1, 1, 12, 0))
        assert "<!DOCTYPE html>" in html
        assert "Últimos 30 dias" in html
        assert "CVE-X" in html and "Crítico" in html
        assert "Vuln Scanner" in html           # rótulo da fonte
        assert "SHA-256" in html
        assert re.search(r"[0-9a-f]{64}", html)  # selo

    def test_escape_xss(self):
        evs = [_ev(title="<script>alert(1)</script>", ref="<b>x</b>")]
        html = rh.build_html("x", {"total": 1}, evs,
                             generated=datetime(2026, 1, 1))
        assert "<script>alert" not in html
        assert "&lt;script&gt;" in html

    def test_vazio(self):
        html = rh.build_html("Tudo", {"total": 0}, [],
                             generated=datetime(2026, 1, 1))
        assert "Nenhum evento" in html

    def test_seal_deterministico(self):
        s = {"total": 1, "by_severity": {"high": 1}, "by_source": {"vuln": 1}}
        evs = [_ev(severity="high", title="a")]
        g = datetime(2026, 1, 1, 12, 0)
        assert rh.build_html("x", s, evs, generated=g) == \
            rh.build_html("x", s, evs, generated=g)
