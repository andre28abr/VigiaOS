"""State local: labels customizados + notas multilinha por deployment.

Limite tecnico: rpm-ostree identifica deployments por checksum SHA-256,
sem campo 'nome customizado'. A nossa solucao: state.json local com
mapping checksum -> {label, notes}.

Arquivo: ~/.config/vigia-deployments/state.json (mode 0600 — LGPD)

Formato:
{
  "labels": {
    "<checksum>": "Pre instalacao do dnscrypt"
  },
  "notes": {
    "<checksum>": "Deployment de 2026-05-20. Instalei chkrootkit pro\\ncliente X. Audit semanal."
  }
}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from vigia_common.state import load_json, save_json_0600


STATE_PATH = Path.home() / ".config" / "vigia-deployments" / "state.json"


@dataclass
class State:
    labels: dict[str, str] = field(default_factory=dict)
    notes: dict[str, str] = field(default_factory=dict)


def _load() -> State:
    """Le state file. Retorna State() vazio se nao existe ou erro."""
    st = State()
    data = load_json(STATE_PATH)
    # HARDENING: arquivo editavel pelo user / corrompivel. Garante shape.
    if isinstance(data, dict):
        labels = data.get("labels", {})
        notes = data.get("notes", {})
        st.labels = dict(labels) if isinstance(labels, dict) else {}
        st.notes = dict(notes) if isinstance(notes, dict) else {}
    return st


def _save(state: State) -> bool:
    """Salva atomico (0600). Retorna True se OK."""
    return save_json_0600(
        STATE_PATH, {"labels": state.labels, "notes": state.notes}
    )


# ============================================================
# API publica
# ============================================================


def get_label(checksum: str) -> str:
    """Retorna label customizado pro checksum, ou '' se nao tem."""
    if not checksum:
        return ""
    return _load().labels.get(checksum, "")


def set_label(checksum: str, label: str) -> bool:
    """Seta label. Empty string remove."""
    if not checksum:
        return False
    state = _load()
    if label.strip():
        state.labels[checksum] = label.strip()
    else:
        state.labels.pop(checksum, None)
    return _save(state)


def get_notes(checksum: str) -> str:
    """Retorna notas multilinha pro checksum."""
    if not checksum:
        return ""
    return _load().notes.get(checksum, "")


def set_notes(checksum: str, notes: str) -> bool:
    """Seta notas. Empty string remove."""
    if not checksum:
        return False
    state = _load()
    if notes.strip():
        state.notes[checksum] = notes
    else:
        state.notes.pop(checksum, None)
    return _save(state)


def cleanup_orphaned(active_checksums: list[str]) -> int:
    """Remove entries do state cujo checksum nao existe mais.

    Chamado periodicamente apos rpm-ostree cleanup. Retorna quantos
    entries foram removidos.
    """
    state = _load()
    active_set = set(active_checksums)
    removed = 0
    for cs in list(state.labels.keys()):
        if cs not in active_set:
            del state.labels[cs]
            removed += 1
    for cs in list(state.notes.keys()):
        if cs not in active_set:
            del state.notes[cs]
            removed += 1
    if removed > 0:
        _save(state)
    return removed
