"""Backend hash.

Operacoes:
- list_algorithms() -> list[str]
- hash_blocking(path, algorithm) -> (hash_value, err)
- verify_blocking(path, expected, algorithm) -> (matches, computed, err)
- create_baseline_blocking(directory, output_file, algorithm) -> BaselineResult
- compare_baseline_blocking(baseline_file, directory, algorithm) -> CompareResult

Usa hashlib (Python stdlib) por padrao. Opcionalmente usa hashdeep
(C, multi-thread) quando instalado, pra ganhar velocidade em arvores
grandes — o hash final e' identico, entao os engines sao intercambiaveis.
Deteccao de arquivo *movido* (mesmo hash, path diferente) e' feita no
compare independente do engine.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
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
    engine: str = "python"  # "python" (hashlib) ou "hashdeep"


@dataclass
class CompareResult:
    baseline_file: str
    directory: str
    algorithm: str
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    moved: list[str] = field(default_factory=list)  # "old -> new" (mesmo hash)
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
    """Calcula hash de um arquivo. Retorna (hash_hex, error).

    Rejeita device files (/dev/zero, /dev/urandom, /proc/kcore, ...) —
    causariam loop infinito de I/O.
    """
    import stat as stat_mod

    if algorithm not in ALGORITHMS:
        return "", f"Algoritmo não suportado: {algorithm}"

    p = Path(path)
    if not p.exists():
        return "", f"Arquivo não existe: {path}"
    if not p.is_file():
        return "", "Caminho não é um arquivo."

    # Hardening: rejeita special files (block/char devices, fifos, sockets,
    # /proc/*, /sys/*). Caso contrario hash de /dev/zero trava infinito.
    try:
        st = p.stat()
        if not stat_mod.S_ISREG(st.st_mode):
            return "", "Caminho não é um arquivo regular (é device/fifo/socket)."
    except OSError as e:
        return "", f"Falha ao stat: {e}"

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
        return False, "", "Hash esperado contém caracteres inválidos."

    computed, err = hash_blocking(path, algorithm)
    if err:
        return False, "", err

    matches = computed.lower() == expected.lower()
    return matches, computed, ""


# ============================================================
# Baseline (snapshot do diretorio)
# ============================================================

_HASHDEEP_ALGOS = {"md5", "sha1", "sha256"}  # hashdeep nao suporta sha512


def _python_hash_dir(d: Path, algorithm: str) -> dict[str, str]:
    """Hash recursivo via hashlib. {path_relativo: hash}."""
    hashes: dict[str, str] = {}
    for f in d.rglob("*"):
        if not f.is_file() or f.is_symlink():
            continue
        try:
            h, _ = hash_blocking(str(f), algorithm)
            if h:
                hashes[str(f.relative_to(d))] = h
        except (OSError, ValueError):
            continue
    return hashes


def _hashdeep_hash_dir(d: Path, algorithm: str) -> dict[str, str] | None:
    """Hash recursivo via hashdeep (rapido em arvores grandes). Parseia o
    formato 'size,hash,filename'. Retorna None se falhar (=> fallback Python)."""
    try:
        proc = subprocess.run(
            ["hashdeep", "-r", "-c", algorithm, "."],
            cwd=str(d), capture_output=True, text=True, timeout=1800,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if proc.returncode != 0:
        return None
    hashes: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if not line or line[0] in "%#":  # header (%%%%) / comentarios (##)
            continue
        parts = line.split(",", 2)  # maxsplit=2: filename pode ter virgulas
        if len(parts) != 3:
            continue
        _size, h, fname = parts
        if fname.startswith("./"):
            fname = fname[2:]
        if fname:
            hashes[fname] = h.strip().lower()
    return hashes


def _hash_dir(
    directory: str, algorithm: str, use_hashdeep: bool
) -> tuple[dict[str, str], str]:
    """Hash recursivo do diretorio. Usa hashdeep se pedido + instalado +
    algo suportado; senao hashlib. Retorna (hashes, engine_usado)."""
    d = Path(directory)
    if use_hashdeep and hashdeep_installed() and algorithm in _HASHDEEP_ALGOS:
        hd = _hashdeep_hash_dir(d, algorithm)
        if hd is not None:
            return hd, "hashdeep"
    return _python_hash_dir(d, algorithm), "python"


def _detect_moves(
    removed: list[str],
    added: list[str],
    expected_hashes: dict[str, str],
    current_hashes: dict[str, str],
) -> tuple[list[str], list[str], list[str]]:
    """Cruza removidos x adicionados: mesmo hash em path diferente = movido.
    Retorna (moved['old -> new'], removed_restante, added_restante)."""
    rem_by_hash: dict[str, list[str]] = {}
    for p in removed:
        rem_by_hash.setdefault(expected_hashes.get(p, ""), []).append(p)
    add_by_hash: dict[str, list[str]] = {}
    for p in added:
        add_by_hash.setdefault(current_hashes.get(p, ""), []).append(p)

    moved: list[str] = []
    moved_rem: set[str] = set()
    moved_add: set[str] = set()
    for h, rem_paths in rem_by_hash.items():
        if not h:
            continue
        add_paths = add_by_hash.get(h, [])
        # pareia 1-a-1 (ordenado = deterministico)
        for old, new in zip(sorted(rem_paths), sorted(add_paths)):
            moved.append(f"{old} → {new}")
            moved_rem.add(old)
            moved_add.add(new)

    removed_left = sorted(set(removed) - moved_rem)
    added_left = sorted(set(added) - moved_add)
    return sorted(moved), removed_left, added_left


def create_baseline_blocking(
    directory: str,
    output_file: str | None = None,
    algorithm: str = "sha256",
    use_hashdeep: bool = False,
) -> BaselineResult:
    """Cria baseline: hash de todos os arquivos no diretorio.

    Output: JSON com {path_relativo: hash}. Se use_hashdeep e o hashdeep
    estiver instalado (e o algo for suportado), usa-o (mais rapido em
    arvores grandes); senao hashlib. O hash final e' identico.
    """
    result = BaselineResult(
        directory=directory,
        algorithm=algorithm,
        output_file="",
        started_at=datetime.now().isoformat(timespec="seconds"),
    )

    if algorithm not in ALGORITHMS:
        result.error = f"Algoritmo não suportado: {algorithm}"
        return result

    d = Path(directory)
    if not d.exists() or not d.is_dir():
        result.error = f"Diretório não existe: {directory}"
        return result

    if output_file:
        outp = Path(output_file)
    else:
        bd = _ensure_baseline_dir()
        safe_ts = result.started_at.replace(":", "-").replace(".", "_")
        safe_name = d.name.replace("/", "_") or "root"
        outp = bd / f"baseline-{safe_name}-{safe_ts}.json"
    result.output_file = str(outp)

    try:
        hashes, result.engine = _hash_dir(str(d), algorithm, use_hashdeep)
        result.file_count = len(hashes)

        # Salva JSON
        data = {
            "directory": str(d.resolve()),
            "algorithm": algorithm,
            "created_at": result.started_at,
            "file_count": result.file_count,
            "engine": result.engine,
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
    use_hashdeep: bool = False,
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
        result.error = f"Baseline não existe: {baseline_file}"
        return result

    try:
        with open(bf, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        result.error = f"Falha ao ler baseline JSON: {e}"
        return result
    # HARDENING: baseline editavel/corrompivel — valida shape antes de usar.
    if not isinstance(data, dict):
        result.error = "Baseline inválido (formato inesperado)."
        return result

    expected_hashes = data.get("hashes", {})
    if not isinstance(expected_hashes, dict):
        expected_hashes = {}
    base_dir = directory or data.get("directory", "")
    if not isinstance(base_dir, str):
        base_dir = ""
    algo = algorithm or data.get("algorithm", "sha256")
    if not isinstance(algo, str):
        algo = "sha256"

    result.directory = base_dir
    result.algorithm = algo

    d = Path(base_dir)
    if not d.exists() or not d.is_dir():
        result.error = f"Diretório não existe: {base_dir}"
        return result

    # Computa estado atual
    try:
        current_hashes, _ = _hash_dir(base_dir, algo, use_hashdeep)
    except (OSError, PermissionError) as e:
        result.error = f"Falha ao escanear: {e}"
        return result

    # Diff
    expected_set = set(expected_hashes.keys())
    current_set = set(current_hashes.keys())

    added = sorted(current_set - expected_set)
    removed = sorted(expected_set - current_set)
    # Detecta movidos (mesmo hash, path diferente) — tira de added/removed.
    moved, removed, added = _detect_moves(
        removed, added, expected_hashes, current_hashes
    )
    result.added = added
    result.removed = removed
    result.moved = moved
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
        except (OSError, json.JSONDecodeError):
            continue
        # HARDENING: pula arquivos com formato inesperado (nao-dict).
        if not isinstance(data, dict):
            continue
        out.append({
            "_file": str(f),
            "directory": data.get("directory", "?"),
            "algorithm": data.get("algorithm", "?"),
            "created_at": data.get("created_at", "?"),
            "file_count": data.get("file_count", 0),
        })
    return out
