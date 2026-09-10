"""RSS em KiB usa o tamanho de página real do kernel (não 4 KiB fixo)."""

from __future__ import annotations

import os

from vigia_dashboard import backend


def test_page_kb_bate_com_sysconf():
    assert backend._PAGE_KB == max(1, os.sysconf("SC_PAGE_SIZE") // 1024)


def test_fallback_4_se_sysconf_falha(monkeypatch):
    monkeypatch.setattr(os, "sysconf", lambda _n: (_ for _ in ()).throw(ValueError()))
    assert backend._page_kb() == 4
