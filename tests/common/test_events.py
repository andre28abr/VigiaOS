"""Testes do banco de eventos (vigia_common.events). Puro: SQLite em tmp_path."""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import pytest

from vigia_common import events


@pytest.fixture
def db(tmp_path):
    # subdir próprio (pra testar perms da pasta sem mexer no tmp_path do pytest)
    return tmp_path / "vigiadata" / "events.db"


# ============================================================
# normalize_severity / severity_rank
# ============================================================


class TestSeverity:
    @pytest.mark.parametrize("inp,exp", [
        ("Alto", "high"), ("alto", "high"), ("HIGH", "high"), ("erro", "high"),
        ("crítico", "critical"), ("critical", "critical"),
        ("Médio", "medium"), ("medio", "medium"), ("suspeito", "medium"),
        ("warning", "medium"), ("aviso", "medium"),
        ("baixo", "low"), ("low", "low"),
        ("info", "info"), ("informativo", "info"), ("teste", "info"),
        ("ok", "ok"), ("limpo", "ok"), ("clean", "ok"),
        ("", "unknown"), ("   ", "unknown"), (None, "unknown"),
        ("custom-sev", "custom-sev"),   # desconhecida é preservada
    ])
    def test_normalize(self, inp, exp):
        assert events.normalize_severity(inp) == exp

    def test_rank_ordem(self):
        assert (events.severity_rank("critical") < events.severity_rank("high")
                < events.severity_rank("medium") < events.severity_rank("info"))

    def test_rank_normaliza_e_desconhecida_no_fim(self):
        assert events.severity_rank("Alto") == events.severity_rank("high")
        assert events.severity_rank("xyz") == len(events.CANON_SEVERITIES)


# ============================================================
# record + query (roundtrip)
# ============================================================


class TestRecordQuery:
    def test_roundtrip(self, db):
        rid = events.record(
            "antivirus", "EICAR encontrado", category="scan", severity="Alto",
            detail="arquivo de teste", ref="/home/u/eicar.txt",
            payload={"k": 1}, db_path=db)
        assert isinstance(rid, int) and rid > 0
        evs = events.query(db_path=db)
        assert len(evs) == 1
        e = evs[0]
        assert e.source == "antivirus" and e.title == "EICAR encontrado"
        assert e.category == "scan"
        assert e.severity == "high"          # normalizada na gravação
        assert e.detail == "arquivo de teste"
        assert e.ref == "/home/u/eicar.txt"
        assert e.payload == {"k": 1}
        assert e.ts and e.ts_epoch > 0

    def test_ts_explicito(self, db):
        when = datetime(2026, 1, 15, 9, 30, 0)
        events.record("a", "x", ts=when, db_path=db)
        e = events.query(db_path=db)[0]
        assert e.ts.startswith("2026-01-15")

    def test_sem_source_ou_title(self, db):
        assert events.record("", "x", db_path=db) is None
        assert events.record("a", "", db_path=db) is None
        assert events.count(db_path=db) == 0

    def test_count_e_distinct(self, db):
        events.record("vuln", "x", db_path=db)
        events.record("antivirus", "y", db_path=db)
        events.record("vuln", "z", db_path=db)
        assert events.count(db_path=db) == 3
        assert events.distinct_sources(db_path=db) == ["antivirus", "vuln"]

    def test_ordena_mais_novo_primeiro(self, db):
        events.record("a", "first", ts=datetime(2026, 1, 1), db_path=db)
        events.record("a", "second", ts=datetime(2026, 2, 1), db_path=db)
        assert [e.title for e in events.query(db_path=db)] == ["second", "first"]


# ============================================================
# Filtros do query
# ============================================================


class TestFilters:
    def _seed(self, db):
        events.record("antivirus", "vírus A", severity="critical",
                      category="scan", ref="/a", ts=datetime(2026, 1, 10), db_path=db)
        events.record("vuln", "CVE B", severity="medium",
                      category="finding", ref="https://x", ts=datetime(2026, 2, 10), db_path=db)
        events.record("rootkit", "suspeito C", severity="low",
                      category="alert", ts=datetime(2026, 3, 10), db_path=db)

    def test_por_source(self, db):
        self._seed(db)
        r = events.query(sources=["vuln"], db_path=db)
        assert [e.title for e in r] == ["CVE B"]

    def test_por_severidade_normaliza(self, db):
        self._seed(db)
        assert len(events.query(severities=["critical"], db_path=db)) == 1
        assert len(events.query(severities=["Médio"], db_path=db)) == 1   # normaliza
        assert len(events.query(severities=["high"], db_path=db)) == 0

    def test_por_categoria(self, db):
        self._seed(db)
        assert len(events.query(categories=["alert"], db_path=db)) == 1

    def test_busca(self, db):
        self._seed(db)
        assert len(events.query(search="CVE", db_path=db)) == 1
        assert len(events.query(search="/a", db_path=db)) == 1     # casa em ref

    def test_periodo(self, db):
        self._seed(db)
        r = events.query(start=datetime(2026, 2, 1), end=datetime(2026, 2, 28),
                         db_path=db)
        assert [e.title for e in r] == ["CVE B"]

    def test_periodo_aceita_iso_e_epoch(self, db):
        self._seed(db)
        assert len(events.query(start="2026-03-01", db_path=db)) == 1
        ep = datetime(2026, 3, 1).timestamp()
        assert len(events.query(start=ep, db_path=db)) == 1

    def test_limit(self, db):
        for i in range(5):
            events.record("a", f"e{i}", ts=datetime(2026, 1, 1 + i), db_path=db)
        assert len(events.query(limit=2, db_path=db)) == 2


# ============================================================
# Agregações
# ============================================================


class TestAggregations:
    def test_summary(self, db):
        events.record("antivirus", "x", severity="high",
                      ts=datetime(2026, 1, 1), db_path=db)
        events.record("antivirus", "y", severity="high",
                      ts=datetime(2026, 1, 2), db_path=db)
        events.record("vuln", "z", severity="critical",
                      ts=datetime(2026, 1, 3), db_path=db)
        s = events.summary(db_path=db)
        assert s["total"] == 3
        assert s["by_source"] == {"antivirus": 2, "vuln": 1}
        assert s["by_severity"] == {"high": 2, "critical": 1}

    def test_summary_periodo(self, db):
        events.record("a", "jan", ts=datetime(2026, 1, 15), db_path=db)
        events.record("a", "feb", ts=datetime(2026, 2, 15), db_path=db)
        s = events.summary(start=datetime(2026, 2, 1), db_path=db)
        assert s["total"] == 1

    def test_counts_by_day(self, db):
        events.record("a", "1", ts=datetime(2026, 1, 1, 10), db_path=db)
        events.record("a", "2", ts=datetime(2026, 1, 1, 15), db_path=db)
        events.record("a", "3", ts=datetime(2026, 1, 2, 10), db_path=db)
        d = dict(events.counts_by_day(db_path=db))
        assert d["2026-01-01"] == 2 and d["2026-01-02"] == 1


# ============================================================
# Retenção / limpeza
# ============================================================


class TestRetention:
    def test_prune(self, db):
        now = datetime.now()
        events.record("a", "velho", ts=now - timedelta(days=400), db_path=db)
        events.record("a", "recente", ts=now - timedelta(days=1), db_path=db)
        removed = events.prune(older_than_days=180, db_path=db)
        assert removed == 1
        rest = events.query(db_path=db)
        assert [e.title for e in rest] == ["recente"]

    def test_prune_vazio(self, db):
        assert events.prune(db_path=db) == 0

    def test_purge_all(self, db):
        events.record("a", "x", db_path=db)
        events.record("a", "y", db_path=db)
        assert events.purge_all(db_path=db) == 2
        assert events.count(db_path=db) == 0


# ============================================================
# Permissões (LGPD) + robustez
# ============================================================


class TestPermsRobustez:
    def test_perms_0600_0700(self, db):
        events.record("a", "x", db_path=db)
        assert os.stat(db).st_mode & 0o777 == 0o600
        assert os.stat(db.parent).st_mode & 0o777 == 0o700

    def test_db_vazio_nao_quebra(self, db):
        assert events.query(db_path=db) == []
        assert events.count(db_path=db) == 0
        assert events.distinct_sources(db_path=db) == []
        assert events.summary(db_path=db)["total"] == 0
        assert events.counts_by_day(db_path=db) == []

    def test_payload_nao_serializavel(self, db):
        rid = events.record("a", "x", payload={"s": {1, 2, 3}}, db_path=db)
        assert rid is not None
        e = events.query(db_path=db)[0]
        assert "s" in e.payload   # set virou string via default=str, mas chave fica
