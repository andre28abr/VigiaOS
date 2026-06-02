"""Backend do Vigia Memory — forense de memória RAM com o Volatility 3.

Wrapper do CLI do **Volatility 3** (`vol` / `vol.py` / `volatility3`). O usuário
aponta um **dump de memória** (capturado antes, ex.: com AVML/LiME) e escolhe um
**plugin** (lista de processos, conexões, código injetado…). Roda
`vol -f <dump> -r json <plugin>` e parseia o JSON numa tabela.

Partes PURAS (testáveis headless, sem volatility e sem gi):
- `PLUGINS` / `plugins()` — catálogo de plugins com descrição leiga.
- `build_vol_cmd(dump, plugin)` — argv (lista, nunca shell string).
- `parse_vol_json(text)` — JSON do Volatility → (colunas, linhas).

> Forense de memória exige um **dump capturado**. O Vigia Memory analisa um dump
> existente **e** pode capturar a RAM desta máquina (AVML via pkexec — ver
> `capture_dump`). A captura exige root e o binário AVML.
"""

from __future__ import annotations

import getpass
import json
import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from vigia_common import proc

# Nomes possíveis do binário do Volatility 3.
_VOL_BINS = ["vol", "vol.py", "volatility3"]


@dataclass
class Plugin:
    id: str                # caminho do plugin no Volatility (ex.: linux.pslist.PsList)
    label: str             # rótulo amigável
    os: str                # "linux" | "windows"
    description: str        # explicação leiga


@dataclass
class MemResult:
    plugin: str
    columns: list[str] = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)
    elapsed_sec: float = 0.0
    error: str = ""
    started_at: str = ""
    raw_tail: str = ""      # cauda da saída crua (debug)


# ============================================================
# Catálogo de plugins (com descrição leiga)
# ============================================================

PLUGINS: list[Plugin] = [
    Plugin("linux.pslist.PsList", "Processos (lista)", "linux",
           "Lista os programas que estavam em execução no momento do dump."),
    Plugin("linux.pstree.PsTree", "Processos (árvore)", "linux",
           "Mostra os processos em árvore — quem iniciou quem (útil p/ achar "
           "processo suspeito criado por outro)."),
    Plugin("linux.bash.Bash", "Histórico do bash", "linux",
           "Recupera os comandos digitados no terminal — ótimo p/ ver o que um "
           "invasor fez."),
    Plugin("linux.lsof.Lsof", "Arquivos abertos", "linux",
           "Arquivos que cada processo tinha aberto."),
    Plugin("linux.sockstat.Sockstat", "Conexões de rede", "linux",
           "Sockets/conexões de rede ativos no momento do dump."),
    Plugin("linux.malfind.Malfind", "Código injetado (malware)", "linux",
           "Procura regiões de memória com cara de código injetado — técnica "
           "comum de malware p/ se esconder."),
    Plugin("windows.pslist.PsList", "Processos (lista)", "windows",
           "Lista os programas em execução (dump de Windows)."),
    Plugin("windows.pstree.PsTree", "Processos (árvore)", "windows",
           "Processos em árvore — quem criou quem (Windows)."),
    Plugin("windows.cmdline.CmdLine", "Linha de comando", "windows",
           "A linha de comando com que cada processo foi iniciado (Windows)."),
    Plugin("windows.netscan.NetScan", "Conexões de rede", "windows",
           "Conexões e sockets de rede encontrados no dump (Windows)."),
    Plugin("windows.malfind.Malfind", "Código injetado (malware)", "windows",
           "Regiões de memória com cara de código injetado (Windows)."),
]


def plugins() -> list[Plugin]:
    return list(PLUGINS)


def get_plugin(pid: str) -> Plugin | None:
    for p in PLUGINS:
        if p.id == pid:
            return p
    return None


# ============================================================
# Sanity
# ============================================================


def vol_binary() -> str | None:
    for b in _VOL_BINS:
        if shutil.which(b):
            return b
    return None


def vol_available() -> bool:
    return vol_binary() is not None


# ============================================================
# Command builder (puro)
# ============================================================


def build_vol_cmd(dump: Path | str, plugin: str, vol_bin: str | None = None) -> list[str]:
    """Argv do Volatility (lista — nunca shell string).

    `vol -f <dump> -r json <plugin>` → saída JSON parseável.
    """
    b = vol_bin or vol_binary() or "vol"
    return [b, "-f", str(dump), "-r", "json", str(plugin)]


# ============================================================
# Parser (puro)
# ============================================================


def parse_vol_json(text: str) -> tuple[list[str], list[dict]]:
    """Saída `-r json` do Volatility (array de objetos) → (colunas, linhas).

    Colunas = união das chaves (na ordem de aparição), descartando as internas
    (`__children` etc.). Nunca crasha.
    """
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError, TypeError):
        return [], []
    if not isinstance(data, list):
        return [], []
    rows = [r for r in data if isinstance(r, dict)]
    columns: list[str] = []
    for r in rows:
        for k in r.keys():
            if isinstance(k, str) and k.startswith("__"):
                continue
            if k not in columns:
                columns.append(k)
    return columns, rows


def row_summary(columns: list[str], row: dict, n: int = 2) -> str:
    """Título curto de uma linha (primeiras n colunas não vazias)."""
    parts: list[str] = []
    for c in columns:
        v = row.get(c)
        if v not in (None, ""):
            parts.append(f"{v}")
        if len(parts) >= n:
            break
    return " · ".join(parts) if parts else "(linha)"


# ============================================================
# Execução (toca o sistema)
# ============================================================


def run_plugin(dump: Path | str, plugin: str, timeout: int = 600,
               max_rows: int = 1000) -> MemResult:
    """Roda um plugin do Volatility sobre o dump e parseia. Nunca levanta."""
    result = MemResult(plugin=plugin,
                       started_at=datetime.now().isoformat(timespec="seconds"))
    if not vol_available():
        result.error = "Volatility 3 não está instalado (vol / vol.py)."
        return result
    if not Path(dump).is_file():
        result.error = f"Dump não encontrado: {dump}"
        return result

    t0 = time.monotonic()
    rc, out, err = proc.run(build_vol_cmd(dump, plugin), timeout=timeout)
    result.elapsed_sec = round(time.monotonic() - t0, 2)
    result.raw_tail = (out or err or "")[-2000:]

    columns, rows = parse_vol_json(out)
    if not rows and rc != 0:
        result.error = (err.strip() or "Falha ao executar o Volatility.")[:500]
    result.columns = columns
    result.rows = rows[:max_rows]
    return result


# ============================================================
# Captura de dump (AVML via pkexec) — opcional, exige root
# ============================================================

# Onde os dumps capturados ficam (padrão do projeto: ~/teste/<modulo>/).
TEST_DIR = Path.home() / "teste" / "memory"

# Helper rodado via pkexec (root): AVML captura a RAM + devolve a posse.
_CAPTURE_HELPER = (
    Path(__file__).resolve().parents[6] / "install" / "_mem_capture.sh"
)

# AVML não vem em repo (binário estático da Microsoft). Procuramos no PATH e em
# locais comuns de instalação do usuário.
_AVML_EXTRA_PATHS = [
    Path.home() / ".local" / "bin" / "avml",
    Path("/usr/local/bin/avml"),
    Path("/usr/bin/avml"),
]


@dataclass
class CaptureResult:
    ok: bool = False
    path: str = ""
    error: str = ""
    elapsed_sec: float = 0.0


def avml_path() -> str | None:
    """Caminho do AVML (PATH ou locais comuns) ou None."""
    found = shutil.which("avml")
    if found:
        return found
    for p in _AVML_EXTRA_PATHS:
        try:
            if p.is_file() and os.access(p, os.X_OK):
                return str(p)
        except OSError:
            continue
    return None


def avml_available() -> bool:
    return avml_path() is not None


def avml_install_hint() -> str:
    return ("AVML não encontrado. Rode ./install/blue-deps.sh (baixa o binário "
            "oficial da Microsoft em ~/.local/bin/avml) — ou instale o AVML "
            "manualmente.")


def default_dump_path() -> Path:
    """Caminho do dump a capturar (~/teste/memory/captura-<timestamp>.lime)."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return TEST_DIR / f"captura-{stamp}.lime"


def build_capture_cmd(out_path: Path | str, avml: str,
                      owner: str | None = None) -> list[str]:
    """Argv do helper de captura via pkexec (lista — nunca shell string)."""
    return ["pkexec", str(_CAPTURE_HELPER), str(avml), str(out_path),
            owner or getpass.getuser()]


def capture_dump(timeout: int = 900) -> CaptureResult:
    """Captura a RAM desta máquina via AVML (helper privilegiado, UM diálogo
    polkit). Salva em ~/teste/memory/ com permissão 0600 (o dump tem dados
    sensíveis). Nunca levanta."""
    res = CaptureResult()
    t0 = time.monotonic()
    avml = avml_path()
    if not avml:
        res.error = avml_install_hint()
        return res
    if not _CAPTURE_HELPER.is_file():
        res.error = "Script de captura não encontrado (instalação não-editável?)."
        return res
    try:
        TEST_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        res.error = f"Não consegui criar ~/teste/memory ({e})."
        return res
    out = default_dump_path()
    rc, _out, err = proc.run(build_capture_cmd(out, avml), timeout=timeout)
    res.elapsed_sec = round(time.monotonic() - t0, 2)
    if rc in (126, 127):
        res.error = "Autenticação cancelada (pkexec)."
        return res
    if rc != 0 or not out.is_file():
        res.error = (err.strip() or "A captura falhou — o AVML não conseguiu ler "
                     "a memória física desta máquina.")[:400]
        return res
    res.ok = True
    res.path = str(out)
    return res
