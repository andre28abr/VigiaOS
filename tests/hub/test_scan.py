"""Testes do vigia-scan — formato do resultado (sem ClamAV no ambiente)."""

from __future__ import annotations

from vigia_hub import scan


def test_scan_returns_well_formed_dict():
    s = scan.scan()
    assert set(s) >= {"ts", "ran", "found", "items"}
    assert isinstance(s["found"], int)
    assert isinstance(s["items"], list)
    # sem clamscan no ambiente de teste → não rodou, nada encontrado
    assert s["found"] == 0


def test_targets_only_existing_dirs():
    for d in scan._targets():
        import os
        assert os.path.isdir(d)
