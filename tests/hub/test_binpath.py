"""Testes do augmentador de PATH (vigia_hub.binpath). Puro, sem GTK, sem FS real."""

from __future__ import annotations

import os

from vigia_hub.binpath import augmented_path, candidate_bin_dirs

SEP = os.pathsep


class TestCandidates:
    def test_inclui_dirs_de_usuario(self):
        c = candidate_bin_dirs("/home/u", {})
        assert "/home/u/.local/bin" in c   # pipx (theHarvester, wapiti)
        assert "/home/u/go/bin" in c       # go install (nuclei)
        assert "/home/u/.cargo/bin" in c   # cargo (Rust)
        assert "/usr/local/bin" in c

    def test_gopath_quando_definido(self):
        c = candidate_bin_dirs("/home/u", {"GOPATH": "/opt/go/"})
        assert "/opt/go/bin" in c

    def test_sem_gopath(self):
        c = candidate_bin_dirs("/home/u", {})
        assert not any("/opt/go" in x for x in c)

    def test_home_com_barra_final(self):
        c = candidate_bin_dirs("/home/u/", {})
        assert "/home/u/go/bin" in c
        assert "/home/u//go/bin" not in c

    def test_home_vazio_nao_quebra(self):
        assert isinstance(candidate_bin_dirs("", {}), list)


class TestAugmented:
    def test_acrescenta_existente_no_fim(self):
        out = augmented_path("/usr/bin", ["/home/u/go/bin"], exists=lambda d: True)
        assert out == f"/usr/bin{SEP}/home/u/go/bin"

    def test_pula_inexistente(self):
        out = augmented_path("/usr/bin", ["/home/u/go/bin"], exists=lambda d: False)
        assert out == "/usr/bin"

    def test_nao_duplica(self):
        out = augmented_path(
            f"/usr/bin{SEP}/home/u/go/bin", ["/home/u/go/bin"], exists=lambda d: True)
        assert out == f"/usr/bin{SEP}/home/u/go/bin"

    def test_idempotente(self):
        once = augmented_path("/usr/bin", ["/a", "/b"], exists=lambda d: True)
        twice = augmented_path(once, ["/a", "/b"], exists=lambda d: True)
        assert once == twice

    def test_path_vazio(self):
        out = augmented_path("", ["/home/u/go/bin"], exists=lambda d: True)
        assert out == "/home/u/go/bin"

    def test_sistema_tem_precedencia(self):
        # extras vão pro FINAL — o que está no sistema ganha.
        out = augmented_path("/usr/bin", ["/home/u/.local/bin"], exists=lambda d: True)
        assert out.split(SEP)[0] == "/usr/bin"

    def test_ordem_estavel(self):
        out = augmented_path("/usr/bin", ["/a", "/b", "/c"], exists=lambda d: True)
        assert out == f"/usr/bin{SEP}/a{SEP}/b{SEP}/c"

    def test_ignora_vazios_no_current(self):
        out = augmented_path(f"{SEP}/usr/bin{SEP}", ["/a"], exists=lambda d: True)
        assert out == f"/usr/bin{SEP}/a"
