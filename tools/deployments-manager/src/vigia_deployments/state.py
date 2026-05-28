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

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


STATE_PATH = Path.home() / ".config" / "vigia-deployments" / "state.json"


@dataclass
class State:
    labels: dict[str, str] = field(default_factory=dict)
    notes: dict[str, str] = field(default_factory=dict)


def _load() -> State:
    """Le state file. Retorna State() vazio se nao existe ou erro."""
    st = State()
    if not STATE_PATH.exists():
        return st
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # HARDENING: arquivo editavel pelo user / corrompivel. Garante shape.
        if isinstance(data, dict):
            labels = data.get("labels", {})
            notes = data.get("notes", {})
            st.labels = dict(labels) if isinstance(labels, dict) else {}
            st.notes = dict(notes) if isinstance(notes, dict) else {}
    except (OSError, json.JSONDecodeError) as e:
        print(f"[state] load falhou: {e}", flush=True)
    return st


def _save(state: State) -> bool:
    """Salva atomico. Retorna True se OK."""
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(STATE_PATH.parent, 0o700)
        tmp = STATE_PATH.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({
                "labels": state.labels,
                "notes": state.notes,
            }, f, ensure_ascii=False, indent=2)
        os.chmod(tmp, 0o600)
        tmp.replace(STATE_PATH)
        return True
    except OSError as e:
        print(f"[state] save falhou: {e}", flush=True)
        return False


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
