"""Regressão do catálogo: Tor de sistema REMOVIDO.

Decisão 2026-05-30 (ver §9 do DEVELOPMENT.md): o Tor Browser (Flatpak) é o
único caminho de Tor no VigiaOS. O daemon `tor` (toggle do Privacy Controls)
e o wrapper CLI `torsocks` saíram do catálogo. Estes testes travam isso
contra reintrodução acidental.

Pure-Python — sem GTK, sem gi.
"""

from __future__ import annotations

from vigia_installer.catalog import (
    CATALOG,
    CATEGORIES_ORDER,
    CATEGORY_DESCRIPTIONS,
    find_by_package,
)


def _packages() -> set[str]:
    return {e.package for e in CATALOG}


class TestTorRemovido:
    def test_sem_daemon_tor(self):
        assert "tor" not in _packages()
        assert find_by_package("tor") is None

    def test_sem_torsocks(self):
        assert "torsocks" not in _packages()
        assert find_by_package("torsocks") is None

    def test_descricao_privacidade_sem_tor(self):
        # a categoria não deve mais anunciar "Tor"
        assert "Tor" not in CATEGORY_DESCRIPTIONS["privacidade"]
        assert "tor" not in CATEGORY_DESCRIPTIONS["privacidade"].lower()


class TestCatalogoIntacto:
    def test_privacidade_mantem_wireguard_e_dnscrypt(self):
        pkgs = _packages()
        assert "wireguard-tools" in pkgs
        assert "dnscrypt-proxy" in pkgs

    def test_total_13_pacotes(self):
        # lock: 15 -> 13 após remover tor + torsocks
        assert len(CATALOG) == 13

    def test_sem_pacotes_duplicados(self):
        pkgs = [e.package for e in CATALOG]
        assert len(pkgs) == len(set(pkgs))

    def test_toda_entry_tem_categoria_valida(self):
        for e in CATALOG:
            assert e.category in CATEGORIES_ORDER
