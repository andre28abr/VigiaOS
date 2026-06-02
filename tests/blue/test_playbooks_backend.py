"""Testes do backend do Vigia Playbooks (catálogo + estado + trilha, sem gi)."""

from __future__ import annotations

import json

from vigia_blue.modules.playbooks import backend

_SEVS = {"info", "baixo", "suspeito", "alto", "critico"}


def test_catalog_shape():
    pbs = backend.playbooks()
    assert len(pbs) == 5
    ids = [p.id for p in pbs]
    assert len(set(ids)) == 5
    for pb in pbs:
        assert pb.title and pb.when
        assert pb.severity in _SEVS
        assert pb.phases and all(ph.steps for ph in pb.phases)


def test_lgpd_playbook_has_notification_phase():
    pb = backend.get_playbook("lgpd_vazamento")
    assert pb is not None
    names = " ".join(ph.name.lower() for ph in pb.phases)
    assert "notificação" in names or "art. 48" in names.lower()


def test_get_playbook_unknown():
    assert backend.get_playbook("nao_existe") is None


def test_total_steps():
    pb = backend.get_playbook("conta_comprometida")
    assert backend.total_steps(pb) == sum(len(ph.steps) for ph in pb.phases)


def test_step_key():
    assert backend.step_key(1, 2) == "1.2"


def test_start_incident():
    pb = backend.get_playbook("malware")
    inc = backend.start_incident(pb)
    assert inc.playbook_id == "malware"
    assert inc.playbook_title == pb.title
    assert inc.started_at and inc.done_steps == [] and inc.closed is False


def test_toggle_step():
    pb = backend.get_playbook("malware")
    inc = backend.start_incident(pb)
    backend.toggle_step(inc, "0.0")
    assert "0.0" in inc.done_steps
    backend.toggle_step(inc, "0.0")
    assert "0.0" not in inc.done_steps


def test_progress_counts_only_valid_keys():
    pb = backend.get_playbook("malware")
    inc = backend.start_incident(pb)
    inc.done_steps = ["0.0", "0.1", "999.999"]  # último é inválido
    done, total = backend.progress(inc, pb)
    assert total == backend.total_steps(pb)
    assert done == 2   # ignora a chave inválida


def test_progress_full():
    pb = backend.get_playbook("conta_comprometida")
    inc = backend.start_incident(pb)
    inc.done_steps = [backend.step_key(pi, si)
                      for pi, ph in enumerate(pb.phases)
                      for si in range(len(ph.steps))]
    done, total = backend.progress(inc, pb)
    assert done == total > 0


def test_save_and_list_incident(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "INCIDENTS_DIR", tmp_path)
    pb = backend.get_playbook("intrusao")
    inc = backend.start_incident(pb)
    inc.done_steps = ["0.0", "0.1"]
    inc.notes = "isolei a máquina"
    path = backend.save_incident(inc)
    assert path is not None and path.exists()
    assert (path.stat().st_mode & 0o777) == 0o600
    data = json.loads(path.read_text())
    assert data["playbook_id"] == "intrusao"
    assert data["notes"] == "isolei a máquina"

    recent = backend.list_incidents()
    assert len(recent) == 1 and recent[0]["playbook_id"] == "intrusao"


def test_list_incidents_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "INCIDENTS_DIR", tmp_path / "vazio")
    assert backend.list_incidents() == []


def test_save_incident_without_timestamp(monkeypatch, tmp_path):
    monkeypatch.setattr(backend, "INCIDENTS_DIR", tmp_path)
    inc = backend.Incident(playbook_id="x", playbook_title="X", started_at="")
    assert backend.save_incident(inc) is None
