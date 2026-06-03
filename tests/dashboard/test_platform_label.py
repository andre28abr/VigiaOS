"""Testes do rotulo de plataforma do hero (Fedora Workstation).

Pure-Python — sem GTK, sem root. Exercita o parser de /etc/os-release
(`_parse_platform`) e o cache de `get_platform_label`.
"""

from __future__ import annotations

import pytest

from vigia_dashboard import backend


# Amostra real de /etc/os-release (recortada).
OSRELEASE_WORKSTATION = (
    'NAME="Fedora Linux"\n'
    'VERSION="44 (Workstation Edition)"\n'
    'ID=fedora\n'
    'VERSION_ID=44\n'
    'VARIANT="Workstation Edition"\n'
    'VARIANT_ID=workstation\n'
    'PRETTY_NAME="Fedora Linux 44 (Workstation Edition)"\n'
)


class TestParsePlatform:
    def test_workstation_strips_edition(self):
        # 'Workstation Edition' -> 'Workstation'
        assert backend._parse_platform(OSRELEASE_WORKSTATION) == "Fedora Workstation"

    def test_name_linux_suffix_stripped(self):
        # 'Fedora Linux' colapsa pra 'Fedora'
        out = backend._parse_platform(OSRELEASE_WORKSTATION)
        assert out.startswith("Fedora ")
        assert "Fedora Linux" not in out

    def test_empty_osrelease_fallback(self):
        # sem /etc/os-release (ex: dev no macOS) -> nao quebra
        assert backend._parse_platform("") == "Linux"

    def test_missing_variant_uses_name_only(self):
        only_name = 'NAME="Fedora Linux"\n'
        assert backend._parse_platform(only_name) == "Fedora"

    def test_quotes_stripped(self):
        out = backend._parse_platform(OSRELEASE_WORKSTATION)
        assert '"' not in out

    def test_no_double_variant_in_label(self):
        # variante aparece uma vez so' (nao 'Fedora Workstation Workstation')
        out = backend._parse_platform(OSRELEASE_WORKSTATION)
        assert out.count("Workstation") == 1


class TestGetPlatformLabel:
    def test_reads_file_and_caches(self, monkeypatch):
        backend._PLATFORM_CACHE = None  # limpa cache entre testes
        calls = {"n": 0}

        def fake_read_text(self, *a, **k):
            calls["n"] += 1
            return OSRELEASE_WORKSTATION

        monkeypatch.setattr(backend.Path, "read_text", fake_read_text)

        label = backend.get_platform_label()
        assert label == "Fedora Workstation"
        # segunda chamada usa cache (nao le o arquivo de novo)
        label2 = backend.get_platform_label()
        assert label2 == label
        assert calls["n"] == 1

    def test_oserror_falls_back(self, monkeypatch):
        backend._PLATFORM_CACHE = None

        def boom(self, *a, **k):
            raise OSError("no such file")

        monkeypatch.setattr(backend.Path, "read_text", boom)
        label = backend.get_platform_label()
        assert label == "Linux"

    @pytest.fixture(autouse=True)
    def _reset_cache(self):
        # garante isolamento: zera o cache antes e depois de cada teste
        backend._PLATFORM_CACHE = None
        yield
        backend._PLATFORM_CACHE = None
