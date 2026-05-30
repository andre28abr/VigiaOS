"""Testes do rotulo de plataforma do hero (Silverblue vs Workstation).

Pure-Python — sem GTK, sem root. Exercita o parser de /etc/os-release
(`_parse_platform`) e o cache de `get_platform_label`.
"""

from __future__ import annotations

import pytest

from vigia_dashboard import backend


# Amostras reais de /etc/os-release (recortadas).
OSRELEASE_SILVERBLUE = (
    'NAME="Fedora Linux"\n'
    'VERSION="44.20260529.0 (Silverblue)"\n'
    'ID=fedora\n'
    'VERSION_ID=44\n'
    'VARIANT="Silverblue"\n'
    'VARIANT_ID=silverblue\n'
    'PRETTY_NAME="Fedora Linux 44.20260529.0 (Silverblue)"\n'
)

OSRELEASE_WORKSTATION = (
    'NAME="Fedora Linux"\n'
    'VERSION="44 (Workstation Edition)"\n'
    'ID=fedora\n'
    'VERSION_ID=44\n'
    'VARIANT="Workstation Edition"\n'
    'VARIANT_ID=workstation\n'
    'PRETTY_NAME="Fedora Linux 44 (Workstation Edition)"\n'
)

OSRELEASE_KINOITE = (
    'NAME="Fedora Linux"\n'
    'VARIANT="Kinoite"\n'
    'VARIANT_ID=kinoite\n'
)


class TestParsePlatform:
    def test_silverblue_atomic(self):
        assert backend._parse_platform(OSRELEASE_SILVERBLUE, True) == (
            "Fedora Silverblue · atômico"
        )

    def test_workstation_strips_edition(self):
        # 'Workstation Edition' -> 'Workstation'; nao-atomico -> tradicional
        assert backend._parse_platform(OSRELEASE_WORKSTATION, False) == (
            "Fedora Workstation · tradicional"
        )

    def test_kinoite_atomic(self):
        assert backend._parse_platform(OSRELEASE_KINOITE, True) == (
            "Fedora Kinoite · atômico"
        )

    def test_name_linux_suffix_stripped(self):
        # 'Fedora Linux' colapsa pra 'Fedora'
        assert backend._parse_platform(OSRELEASE_SILVERBLUE, True).startswith(
            "Fedora Silverblue"
        )
        assert "Fedora Linux" not in backend._parse_platform(
            OSRELEASE_SILVERBLUE, True
        )

    def test_qualifier_follows_atomic_flag(self):
        # mesmo conteudo, qualificador muda so' pelo flag atomic
        atomic = backend._parse_platform(OSRELEASE_SILVERBLUE, True)
        trad = backend._parse_platform(OSRELEASE_SILVERBLUE, False)
        assert atomic.endswith("· atômico")
        assert trad.endswith("· tradicional")

    def test_empty_osrelease_fallback(self):
        # sem /etc/os-release (ex: dev no macOS) -> nao quebra
        assert backend._parse_platform("", False) == "Linux · tradicional"
        assert backend._parse_platform("", True) == "Linux · atômico"

    def test_missing_variant_uses_name_only(self):
        only_name = 'NAME="Fedora Linux"\n'
        assert backend._parse_platform(only_name, False) == "Fedora · tradicional"

    def test_quotes_stripped(self):
        # valores entre aspas sao limpos
        out = backend._parse_platform(OSRELEASE_WORKSTATION, False)
        assert '"' not in out

    def test_no_double_variant_in_label(self):
        # variante aparece uma vez so' (nao 'Fedora Silverblue Silverblue')
        out = backend._parse_platform(OSRELEASE_SILVERBLUE, True)
        assert out.count("Silverblue") == 1


class TestGetPlatformLabel:
    def test_reads_file_and_caches(self, monkeypatch):
        backend._PLATFORM_CACHE = None  # limpa cache entre testes
        calls = {"n": 0}

        def fake_read_text(self, *a, **k):
            calls["n"] += 1
            return OSRELEASE_SILVERBLUE

        monkeypatch.setattr(backend, "is_atomic", lambda: True)
        monkeypatch.setattr(backend.Path, "read_text", fake_read_text)

        label, atomic = backend.get_platform_label()
        assert label == "Fedora Silverblue · atômico"
        assert atomic is True
        # segunda chamada usa cache (nao le o arquivo de novo)
        label2, atomic2 = backend.get_platform_label()
        assert (label2, atomic2) == (label, atomic)
        assert calls["n"] == 1

    def test_workstation_not_atomic(self, monkeypatch):
        backend._PLATFORM_CACHE = None
        monkeypatch.setattr(backend, "is_atomic", lambda: False)
        monkeypatch.setattr(
            backend.Path, "read_text", lambda self, *a, **k: OSRELEASE_WORKSTATION
        )
        label, atomic = backend.get_platform_label()
        assert label == "Fedora Workstation · tradicional"
        assert atomic is False

    def test_oserror_falls_back(self, monkeypatch):
        backend._PLATFORM_CACHE = None

        def boom(self, *a, **k):
            raise OSError("no such file")

        monkeypatch.setattr(backend, "is_atomic", lambda: False)
        monkeypatch.setattr(backend.Path, "read_text", boom)
        label, atomic = backend.get_platform_label()
        assert label == "Linux · tradicional"
        assert atomic is False

    @pytest.fixture(autouse=True)
    def _reset_cache(self):
        # garante isolamento: zera o cache antes e depois de cada teste
        backend._PLATFORM_CACHE = None
        yield
        backend._PLATFORM_CACHE = None
