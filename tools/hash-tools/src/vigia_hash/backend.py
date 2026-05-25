"""Backend hash.

Operacoes:
- list_algorithms() -> list[str]
- hash_blocking(path, algorithm) -> (hash_value, err)
- verify_blocking(path, expected, algorithm) -> (matches, computed, err)
- create_baseline_blocking(directory, output_file, algorithm) -> BaselineResult
- compare_baseline_blocking(baseline_file, directory, algorithm) -> CompareResult

Usa hashlib (Python stdlib) — sem subprocess. Em diretorios grandes
(>10k arquivos), considera hashdeep paralelo em v0.2.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


BASELINE_DIR = Path.home() / ".local" / "share" / "vigia-hash"


ALGORITHMS = ["sha256", "sha512", "sha1", "md5"]


@dataclass
class BaselineResult:
    directory: str
    algorithm: str
    output_file: str
    file_count: int = 0
    error: str = ""
    started_at: str = ""


@dataclass
class CompareResult:
    baseline_file: str
    directory: str
    algorithm: str
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    unchanged: int = 0
    error: str = ""
    started_at: str = ""


# ============================================================
# Sanity
# ============================================================


def hashdeep_installed() -> bool:
    return shutil.which("hashdeep") is not None


def coreutils_installed() -> bool:
    return shutil.which("sha256sum") is not None  # sempre vem por default


def list_algorithms() -> list[str]:
    return list(ALGORITHMS)


def _ensure_baseline_dir() -> Path:
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(BASELINE_DIR, 0o700)
    except OSError:
        pass
    return BASELINE_DIR


# ============================================================
# Hash single
# ============================================================


def hash_blocking(path: str, algorithm: str = "sha256") -> tuple[str, str]:
    """Calcula hash de um arquivo. Retorna (hash_hex, error)."""
    if algorithm not in ALGORITHMS:
        return "", f"Algoritmo nao suportado: {algorithm}"

    p = Path(path)
    if not p.exists():
        return "", f"Arquivo nao existe: {path}"
    if not p.is_file():
        return "", "Caminho nao e' um arquivo."

    try:
        h = hashlib.new(algorithm)
        with open(p, "rb") as f:
            while True:
                chunk = f.read(1 << 20)  # 1 MB
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest(), ""
    except (OSError, PermissionError) as e:
        return "", f"Falha ao ler arquivo: {e}"


# ============================================================
# Verify
# ============================================================


def verify_blocking(
    path: str, expected: str, algorithm: str = "sha256"
) -> tuple[bool, str, str]:
    """Compara hash conhecido com computado.

    Retorna (matches, computed_hash, error).
    """
    expected = expected.strip().lower()
    if not expected:
        return False, "", "Hash esperado vazio."

    # Aceita "<hash>  <filename>" (formato sha256sum) e separa
    if " " in expected or "\t" in expected:
        expected = expected.split()[0]

    if not all(c in "0123456789abcdef" for c in expected):
        return False, "", "Hash esperado contem caracteres invalidos."

    computed, err = hash_blocking(path, algorithm)
    if err:
        return False, "", err

    matches = computed.lower() == expected.lower()
    return matches, computed, ""


# ============================================================
# Baseline (snapshot do diretorio)
# ============================================================


def create_baseline_blocking(
    directory: str,
    output_file: str | None = None,
    algorithm: str = "sha256",
) -> BaselineResult:
    """Cria baseline: hash de todos os arquivos no diretorio.

    Output: JSON com {path_relativo: hash}.
    """
    result = BaselineResult(
        directory=directory,
        algorithm=algorithm,
        output_file="",
        started_at=datetime.now().isoformat(timespec="seconds"),
    )

    if algorithm not in ALGORITHMS:
        result.error = f"Algoritmo nao suportado: {algorithm}"
        return result

    d = Path(directory)
    if not d.exists() or not d.is_dir():
        result.error = f"Diretorio nao existe: {directory}"
        return result

    if output_file:
        outp = Path(output_file)
    else:
        bd = _ensure_baseline_dir()
        safe_ts = result.started_at.replace(":", "-").replace(".", "_")
        safe_name = d.name.replace("/", "_") or "root"
        outp = bd / f"baseline-{safe_name}-{safe_ts}.json"
    result.output_file = str(outp)

    hashes: dict[str, str] = {}
    try:
        for f in d.rglob("*"):
            if not f.is_file() or f.is_symlink():
                continue
            try:
                h, err = hash_blocking(str(f), algorithm)
                if h:
                    rel = str(f.relative_to(d))
                    hashes[rel] = h
            except (OSError, ValueError):
                continue

        result.file_count = len(hashes)

        # Salva JSON
        data = {
            "directory": str(d.resolve()),
            "algorithm": algorithm,
            "created_at": result.started_at,
            "file_count": result.file_count,
            "hashes": hashes,
        }
        with open(outp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        try:
            os.chmod(outp, 0o600)
        except OSError:
            pass
    except (OSError, PermissionError) as e:
        result.error = f"Falha ao criar baseline: {e}"

    return result


def compare_baseline_blocking(
    baseline_file: str,
    directory: str | None = None,
    algorithm: str | None = None,
) -> CompareResult:
    """Compara baseline JSON com estado atual.

    Args:
        baseline_file: caminho do JSON.
        directory: se None, usa o do baseline.
        algorithm: se None, usa o do baseline.
    """
    result = CompareResult(
        baseline_file=baseline_file,
        directory=directory or "",
        algorithm=algorithm or "",
        started_at=datetime.now().isoformat(timespec="seconds"),
    )

    bf = Path(baseline_file)
    if not bf.exists() or not bf.is_file():
        result.error = f"Baseline nao existe: {baseline_file}"
        return result

    try:
        with open(bf, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        result.error = f"Falha ao ler baseline JSON: {e}"
        return result

    expected_hashes = data.get("hashes", {})
    base_dir = directory or data.get("directory", "")
    algo = algorithm or data.get("algorithm", "sha256")

    result.directory = base_dir
    result.algorithm = algo

    d = Path(base_dir)
    if not d.exists() or not d.is_dir():
        result.error = f"Diretorio nao existe: {base_dir}"
        return result

    # Computa estado atual
    current_hashes: dict[str, str] = {}
    try:
        for f in d.rglob("*"):
            if not f.is_file() or f.is_symlink():
                continue
            try:
                h, _ = hash_blocking(str(f), algo)
                if h:
                    rel = str(f.relative_to(d))
                    current_hashes[rel] = h
            except (OSError, ValueError):
                continue
    except (OSError, PermissionError) as e:
        result.error = f"Falha ao escanear: {e}"
        return result

    # Diff
    expected_set = set(expected_hashes.keys())
    current_set = set(current_hashes.keys())

    result.added = sorted(current_set - expected_set)
    result.removed = sorted(expected_set - current_set)
    for path in expected_set & current_set:
        if expected_hashes[path] != current_hashes[path]:
            result.modified.append(path)
        else:
            result.unchanged += 1
    result.modified.sort()

    return result


def list_baselines() -> list[dict]:
    """Lista baselines criados pelo Vigia."""
    if not BASELINE_DIR.is_dir():
        return []
    files = sorted(BASELINE_DIR.glob("baseline-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            out.append({
                "_file": str(f),
                "directory": data.get("directory", "?"),
                "algorithm": data.get("algorithm", "?"),
                "created_at": data.get("created_at", "?"),
                "file_count": data.get("file_count", 0),
            })
        except (OSError, json.JSONDecodeError):
            continue
    return out
