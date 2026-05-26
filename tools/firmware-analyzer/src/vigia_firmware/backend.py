"""Backend binwalk.

Operacoes:
- binwalk_installed() -> bool
- analyze_blocking(path) -> AnalyzeResult
- extract_blocking(path, outdir) -> ExtractResult
- entropy_blocking(path) -> EntropyResult

Sem pkexec — binwalk roda como user em arquivos que o user le.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Signature:
    offset: int             # bytes do inicio
    offset_hex: str         # "0x1000"
    description: str        # ex: "JPEG image data, JFIF standard 1.01"


@dataclass
class AnalyzeResult:
    target: str
    signatures: list[Signature] = field(default_factory=list)
    elapsed_sec: float = 0.0
    error: str = ""
    raw_output: str = ""


@dataclass
class ExtractResult:
    target: str
    outdir: str
    file_count: int = 0
    elapsed_sec: float = 0.0
    error: str = ""
    raw_output: str = ""


@dataclass
class EntropyPoint:
    offset: int
    entropy: float          # 0.0 a 1.0


@dataclass
class EntropyResult:
    target: str
    points: list[EntropyPoint] = field(default_factory=list)
    elapsed_sec: float = 0.0
    error: str = ""
    raw_output: str = ""


# ============================================================
# Sanity
# ============================================================


def binwalk_installed() -> bool:
    return shutil.which("binwalk") is not None


def _run(cmd: list[str], timeout: int = 180) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 1, "", ""


def _validate_path(path: str) -> tuple[bool, str]:
    if not path:
        return False, "Caminho vazio."
    p = Path(path)
    if not p.exists():
        return False, f"Arquivo nao existe: {path}"
    if not p.is_file():
        return False, "Caminho nao e' um arquivo."
    if not p.is_absolute():
        return False, "Use caminho absoluto."
    return True, ""


# ============================================================
# Analyze (signatures)
# ============================================================


def analyze_blocking(path: str) -> AnalyzeResult:
    """`binwalk <path>`. Detecta signatures de arquivos embarcados."""
    result = AnalyzeResult(target=path)

    if not binwalk_installed():
        result.error = "binwalk nao instalado. Instale com: rpm-ostree install binwalk"
        return result

    ok, err = _validate_path(path)
    if not ok:
        result.error = err
        return result

    start = time.time()
    rc, out, err_text = _run(["binwalk", "--", path], timeout=300)
    result.elapsed_sec = round(time.time() - start, 2)

    if not out:
        result.error = err_text.strip() or "binwalk nao retornou output."
        return result

    result.raw_output = out
    result.signatures = _parse_binwalk_output(out)

    if rc != 0 and not result.signatures:
        result.error = (err_text or out).strip()[:500]

    return result


def _parse_binwalk_output(text: str) -> list[Signature]:
    """Parseia output do binwalk.

    Formato tipico:
        DECIMAL       HEXADECIMAL     DESCRIPTION
        --------------------------------------------------------------------------------
        0             0x0             JPEG image data, JFIF standard 1.01
        1024          0x400           Zip archive data
    """
    sigs: list[Signature] = []
    in_data = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith("DECIMAL"):
            in_data = True
            continue
        if line.startswith("---") or line.startswith("==="):
            continue
        if not in_data:
            continue

        # split em pelo menos 3 colunas (decimal, hex, description)
        m = re.match(r"^\s*(\d+)\s+(0x[0-9a-fA-F]+)\s+(.+)$", line)
        if m:
            sigs.append(Signature(
                offset=int(m.group(1)),
                offset_hex=m.group(2),
                description=m.group(3).strip(),
            ))
    return sigs


# ============================================================
# Extract
# ============================================================


def extract_blocking(path: str, outdir: str) -> ExtractResult:
    """`binwalk -e --directory=<outdir> <path>`. Extrai arquivos embarcados."""
    result = ExtractResult(target=path, outdir=outdir)

    if not binwalk_installed():
        result.error = "binwalk nao instalado."
        return result

    ok, err = _validate_path(path)
    if not ok:
        result.error = err
        return result

    outp = Path(outdir)
    try:
        outp.mkdir(parents=True, exist_ok=True)
        # LGPD: firmware extraido pode conter PII de devices (camera IP de
        # cliente, NAS de escritorio). 0700 garante apenas o user le.
        os.chmod(outp, 0o700)
    except OSError as e:
        result.error = f"Falha ao criar outdir: {e}"
        return result

    start = time.time()
    cmd = ["binwalk", "-e", "--directory", str(outp), "--", path]
    rc, out, err_text = _run(cmd, timeout=600)
    result.elapsed_sec = round(time.time() - start, 2)

    result.raw_output = out

    if rc != 0 and not out:
        result.error = (err_text or "binwalk falhou.").strip()[:500]
        return result

    # binwalk -e cria um subdir chamado "_<filename>.extracted" dentro do outdir
    extracted_dirs = list(outp.glob("_*.extracted"))
    count = 0
    for d in extracted_dirs:
        try:
            count += sum(1 for _ in d.rglob("*") if _.is_file())
        except OSError:
            pass
    result.file_count = count

    return result


# ============================================================
# Entropy
# ============================================================


def entropy_blocking(path: str) -> EntropyResult:
    """`binwalk -E -J <path>`. Calcula entropia ao longo do arquivo.

    Nesta v0.1, parseamos output texto. v0.2 vai usar -J (json) quando
    disponivel (depende da versao do binwalk).
    """
    result = EntropyResult(target=path)

    if not binwalk_installed():
        result.error = "binwalk nao instalado."
        return result

    ok, err = _validate_path(path)
    if not ok:
        result.error = err
        return result

    start = time.time()
    # -E entropia; --nplot evita matplotlib (so texto); --nlegend
    rc, out, err_text = _run(
        ["binwalk", "-E", "--nplot", "--", path],
        timeout=600,
    )
    result.elapsed_sec = round(time.time() - start, 2)
    result.raw_output = out

    if not out:
        result.error = err_text.strip() or "binwalk -E nao retornou output."
        return result

    result.points = _parse_entropy_output(out)

    if rc != 0 and not result.points:
        result.error = (err_text or out).strip()[:500]

    return result


def _parse_entropy_output(text: str) -> list[EntropyPoint]:
    """Parseia output -E. Formato similar ao analyze.

    Linhas tipo:
        0             0x0             Rising entropy edge (0.987695)
        4096          0x1000          Falling entropy edge (0.123456)

    binwalk -E mostra apenas edges; para curva completa precisariamos
    de --jsonp ou parsing binario. Nesta v0.1 reportamos os edges.
    """
    points: list[EntropyPoint] = []
    in_data = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith("DECIMAL"):
            in_data = True
            continue
        if line.startswith("---") or line.startswith("==="):
            continue
        if not in_data:
            continue

        m = re.match(r"^\s*(\d+)\s+(0x[0-9a-fA-F]+)\s+(.+)$", line)
        if not m:
            continue
        desc = m.group(3)
        # extrai valor entropia entre parenteses
        ent_m = re.search(r"\(([\d.]+)\)", desc)
        if ent_m:
            try:
                points.append(EntropyPoint(
                    offset=int(m.group(1)),
                    entropy=float(ent_m.group(1)),
                ))
            except ValueError:
                continue

    return points
