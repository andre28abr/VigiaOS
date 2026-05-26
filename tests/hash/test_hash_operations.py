"""Testes para vigia_hash.backend.

Hash, verify, baseline. Algoritmos. Edge cases.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

import pytest

from vigia_hash.backend import (
    ALGORITHMS,
    compare_baseline_blocking,
    create_baseline_blocking,
    hash_blocking,
    list_algorithms,
    verify_blocking,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def temp_file():
    """Cria arquivo temporario com conteudo conhecido."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        f.write(b"hello world\n")
        path = f.name
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def temp_empty_file():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        path = f.name
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def temp_binary_file():
    """Arquivo com bytes binarios (incluindo \\x00)."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
        f.write(bytes(range(256)))  # 0x00 a 0xFF
        path = f.name
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


# ============================================================
# Algoritmos disponiveis
# ============================================================


class TestAlgorithms:
    def test_list_algorithms_returns_list(self):
        algs = list_algorithms()
        assert isinstance(algs, list)
        assert len(algs) > 0

    def test_sha256_is_in_list(self):
        assert "sha256" in list_algorithms()

    def test_sha512_is_in_list(self):
        assert "sha512" in list_algorithms()

    def test_md5_is_in_list(self):
        # Legacy mas suportado
        assert "md5" in list_algorithms()

    def test_algorithms_constant_matches_list(self):
        assert list(list_algorithms()) == list(ALGORITHMS)


# ============================================================
# hash_blocking
# ============================================================


class TestHashBlocking:
    def test_sha256_known_value(self, temp_file):
        """SHA-256 de 'hello world\\n' eh um valor conhecido."""
        h, err = hash_blocking(temp_file, "sha256")
        assert err == ""
        # 'hello world\n' → SHA-256
        expected = hashlib.sha256(b"hello world\n").hexdigest()
        assert h == expected

    def test_md5_known_value(self, temp_file):
        h, err = hash_blocking(temp_file, "md5")
        assert err == ""
        expected = hashlib.md5(b"hello world\n").hexdigest()
        assert h == expected

    def test_empty_file(self, temp_empty_file):
        h, err = hash_blocking(temp_empty_file, "sha256")
        assert err == ""
        # SHA-256 of empty
        assert h == hashlib.sha256(b"").hexdigest()

    def test_binary_file(self, temp_binary_file):
        h, err = hash_blocking(temp_binary_file, "sha256")
        assert err == ""
        expected = hashlib.sha256(bytes(range(256))).hexdigest()
        assert h == expected

    def test_nonexistent_file(self):
        h, err = hash_blocking("/nonexistent/path/file.txt", "sha256")
        assert h == ""
        assert err  # deve ter mensagem de erro

    def test_invalid_algorithm(self, temp_file):
        h, err = hash_blocking(temp_file, "blake3")  # nao suportado em v0.1
        assert h == ""
        assert "nao suportado" in err.lower() or "invalido" in err.lower() or err

    def test_directory_as_input(self, tmp_path):
        # Passar diretorio em vez de arquivo
        h, err = hash_blocking(str(tmp_path), "sha256")
        assert h == ""
        assert err

    @pytest.mark.skipif(
        not Path("/dev/zero").exists(),
        reason="device files apenas em Linux/Unix",
    )
    def test_device_file_rejected(self):
        """SECURITY: /dev/zero, /dev/urandom etc travariam I/O. Devem ser rejeitados."""
        h, err = hash_blocking("/dev/zero", "sha256")
        assert h == ""
        assert err
        # Mensagem deve indicar problema com tipo de arquivo
        assert "arquivo" in err.lower() or "regular" in err.lower() or "device" in err.lower()


# ============================================================
# verify_blocking
# ============================================================


class TestVerifyBlocking:
    def test_correct_hash(self, temp_file):
        # Calcula hash, depois verifica
        h, _ = hash_blocking(temp_file, "sha256")
        matches, computed, err = verify_blocking(temp_file, h, "sha256")
        assert matches is True
        assert computed == h
        assert err == ""

    def test_wrong_hash(self, temp_file):
        wrong = "0" * 64
        matches, computed, err = verify_blocking(temp_file, wrong, "sha256")
        assert matches is False
        assert err == ""

    def test_hash_with_filename_suffix(self, temp_file):
        """Aceita formato 'hash  filename' (output do sha256sum)."""
        h, _ = hash_blocking(temp_file, "sha256")
        formatted = f"{h}  somefile.txt"
        matches, _, err = verify_blocking(temp_file, formatted, "sha256")
        assert matches is True
        assert err == ""

    def test_hash_with_tab_separator(self, temp_file):
        h, _ = hash_blocking(temp_file, "sha256")
        formatted = f"{h}\tsomefile"
        matches, _, err = verify_blocking(temp_file, formatted, "sha256")
        assert matches is True

    def test_uppercase_hash(self, temp_file):
        h, _ = hash_blocking(temp_file, "sha256")
        matches, _, err = verify_blocking(temp_file, h.upper(), "sha256")
        assert matches is True  # case-insensitive

    def test_invalid_hash_chars(self, temp_file):
        bad = "not-a-hex-string-zzzzz"
        matches, _, err = verify_blocking(temp_file, bad, "sha256")
        assert matches is False
        assert "invalid" in err.lower() or err

    def test_empty_expected(self, temp_file):
        matches, _, err = verify_blocking(temp_file, "", "sha256")
        assert matches is False
        assert err


# ============================================================
# Baseline create + compare
# ============================================================


class TestBaseline:
    def test_create_baseline_basic(self, tmp_path):
        """Use case correto: baseline FORA do dir sendo hasheado."""
        # Dir com 3 arquivos
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "a.txt").write_text("a content")
        (data_dir / "b.txt").write_text("b content")
        (data_dir / "c.txt").write_text("c content")

        # Baseline FORA do data_dir
        baseline_file = tmp_path / "baseline.json"

        result = create_baseline_blocking(
            str(data_dir), str(baseline_file), "sha256"
        )

        assert result.error == ""
        assert result.file_count == 3
        assert baseline_file.exists()

    def test_compare_baseline_no_changes(self, tmp_path):
        """Use case correto: baseline FORA do dir hasheado."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "a.txt").write_text("a content")
        (data_dir / "b.txt").write_text("b content")

        baseline_file = tmp_path / "baseline.json"
        create_baseline_blocking(str(data_dir), str(baseline_file), "sha256")

        # Compara sem mudar nada
        result = compare_baseline_blocking(str(baseline_file), str(data_dir))
        assert result.error == ""
        assert result.added == []
        assert result.removed == []
        assert result.modified == []

    def test_baseline_inside_target_dir_documenta_gap(self, tmp_path):
        """LIMITACAO conhecida: se baseline.json esta DENTRO do diretorio
        sendo hasheado, ele aparece como 'added' no compare seguinte
        (porque rglob pega ele e nao estava no baseline original).

        Fix sugerido: create_baseline_blocking deveria excluir o
        output_file da varredura quando o output_file estiver dentro
        do directory.

        Aqui apenas documenta o comportamento atual.
        """
        (tmp_path / "a.txt").write_text("a content")
        baseline_file = tmp_path / "baseline.json"  # DENTRO do tmp_path

        create_baseline_blocking(str(tmp_path), str(baseline_file), "sha256")

        result = compare_baseline_blocking(str(baseline_file), str(tmp_path))
        # bug-by-design: baseline.json aparece como 'added'
        assert "baseline.json" in result.added

    def test_compare_baseline_modified_file(self, tmp_path):
        # Baseline FORA do data_dir
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        a = data_dir / "a.txt"
        a.write_text("original content")

        baseline_file = tmp_path / "baseline.json"
        create_baseline_blocking(str(data_dir), str(baseline_file), "sha256")

        # Modifica
        a.write_text("MODIFIED content")

        result = compare_baseline_blocking(str(baseline_file), str(data_dir))
        assert "a.txt" in result.modified

    def test_compare_baseline_added_file(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "a.txt").write_text("a content")
        baseline_file = tmp_path / "baseline.json"
        create_baseline_blocking(str(data_dir), str(baseline_file), "sha256")

        # Adiciona arquivo novo
        (data_dir / "new.txt").write_text("new content")

        result = compare_baseline_blocking(str(baseline_file), str(data_dir))
        assert "new.txt" in result.added

    def test_compare_baseline_removed_file(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        a = data_dir / "a.txt"
        a.write_text("a content")
        baseline_file = tmp_path / "baseline.json"
        create_baseline_blocking(str(data_dir), str(baseline_file), "sha256")

        # Remove
        a.unlink()

        result = compare_baseline_blocking(str(baseline_file), str(data_dir))
        assert "a.txt" in result.removed

    def test_baseline_nonexistent(self):
        result = compare_baseline_blocking(
            "/nonexistent/baseline.json", "/tmp"
        )
        assert result.error
