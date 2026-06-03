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
import subprocess
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


def build_vol_cmd(dump: Path | str, plugin: str, vol_bin: str | None = None,
                  symbols_dir: Path | str | None = None) -> list[str]:
    """Argv do Volatility (lista — nunca shell string).

    `vol [-s <symbols>] -f <dump> -r json <plugin>` → saída JSON parseável.
    `symbols_dir` (se existir) é passado com `-s`: é onde colocamos os ISF do
    kernel Linux que geramos (ver `generate_symbols`).
    """
    b = vol_bin or vol_binary() or "vol"
    cmd = [b]
    if symbols_dir and Path(symbols_dir).is_dir():
        cmd += ["-s", str(symbols_dir)]
    cmd += ["-f", str(dump), "-r", "json", str(plugin)]
    return cmd


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
    rc, out, err = proc.run(
        build_vol_cmd(dump, plugin, symbols_dir=SYMBOLS_DIR), timeout=timeout)
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


# ============================================================
# Símbolos do kernel (ISF) — pra analisar dumps de Linux
# ============================================================

# O Volatility procura símbolos extras passados via `-s`. Geramos os ISF do
# kernel aqui e apontamos o vol pra cá (ver build_vol_cmd / run_plugin).
SYMBOLS_DIR = TEST_DIR / "symbols"

_DWARF2JSON_EXTRA = [
    Path.home() / ".local" / "bin" / "dwarf2json",
    Path("/usr/local/bin/dwarf2json"),
]


@dataclass
class SymbolsResult:
    ok: bool = False
    banner: str = ""        # "Linux version 6.x ..."
    release: str = ""       # "6.x.x-..." extraído do banner
    isf_path: str = ""      # ISF gerado (quando ok)
    message: str = ""       # resumo pro usuário
    steps: str = ""         # passos copiáveis (quando não dá pra automatizar)


def is_symbols_error(text: str) -> bool:
    """True se o erro do Volatility é falta de símbolos do kernel (ISF)."""
    t = (text or "").lower()
    return ("symbol_table_name" in t
            or "unable to validate the plugin requirements" in t)


def dwarf2json_path() -> str | None:
    found = shutil.which("dwarf2json")
    if found:
        return found
    for p in _DWARF2JSON_EXTRA:
        try:
            if p.is_file() and os.access(p, os.X_OK):
                return str(p)
        except OSError:
            continue
    return None


def _release_from_banner(banner: str) -> str:
    """'Linux version 6.8.0-... (builder@…)' → '6.8.0-...'."""
    parts = (banner or "").split()
    if len(parts) >= 3 and parts[0] == "Linux" and parts[1] == "version":
        return parts[2]
    return ""


def dump_banner(dump: Path | str, timeout: int = 300) -> str:
    """Banner do kernel do dump (`vol banners.Banners` — NÃO precisa de
    símbolos). Retorna a string 'Linux version …' ou ''."""
    b = vol_binary()
    if not b or not Path(dump).is_file():
        return ""
    _rc, out, _err = proc.run(
        [b, "-f", str(dump), "-r", "json", "banners.Banners"], timeout=timeout)
    _cols, rows = parse_vol_json(out)
    for r in rows:
        for v in r.values():
            if isinstance(v, str) and "Linux version" in v:
                return v.strip()
    return ""


def _find_vmlinux(release: str) -> str | None:
    """Procura um vmlinux com DWARF (kernel-debuginfo) pro release."""
    if not release:
        return None
    for c in (Path(f"/usr/lib/debug/lib/modules/{release}/vmlinux"),
              Path(f"/usr/lib/debug/usr/lib/modules/{release}/vmlinux"),
              Path(f"/lib/modules/{release}/build/vmlinux")):
        if c.is_file():
            return str(c)
    return None


def symbols_steps(release: str) -> str:
    """Receita completa e copiável pra gerar os símbolos no Fedora via toolbox.

    O toolbox compartilha o $HOME, então o ISF cai direto em
    ~/teste/memory/symbols/ e o Vigia (no host) acha sozinho via `-s`.
    """
    rel = release or "$(uname -r)"
    return (
        "No Fedora/Silverblue, gere os símbolos num toolbox (não suja o "
        "sistema). Cole isto no terminal:\n\n"
        "  toolbox create -y && toolbox enter\n"
        "  # --- dentro do toolbox: ---\n"
        "  sudo dnf install -y golang\n"
        "  go install github.com/volatilityfoundation/dwarf2json@latest\n"
        f"  sudo dnf debuginfo-install -y kernel-core-{rel}\n"
        "  mkdir -p ~/teste/memory/symbols/linux\n"
        "  ~/go/bin/dwarf2json linux --elf \\\n"
        f"    /usr/lib/debug/lib/modules/{rel}/vmlinux \\\n"
        f"    > ~/teste/memory/symbols/linux/{rel}.json\n"
        "  exit\n\n"
        "Depois, aqui no Vigia, é só clicar em Analisar de novo — agora vai."
    )


def generate_symbols(dump: Path | str) -> SymbolsResult:
    """Tenta gerar o ISF do kernel do dump. Automatiza se dwarf2json + um
    vmlinux (debuginfo) existirem; senão devolve os passos. Nunca levanta."""
    res = SymbolsResult()
    res.banner = dump_banner(dump)
    res.release = _release_from_banner(res.banner)
    if not res.banner:
        res.message = ("Não consegui ler o banner do kernel no dump. Ele é de "
                       "Linux? A captura terminou direito?")
        return res
    if not dwarf2json_path():
        res.message = ("Falta o dwarf2json (gera os símbolos a partir do "
                       "kernel). Rode ./install/blue-deps.sh.")
        res.steps = symbols_steps(res.release)
        return res
    vmlinux = _find_vmlinux(res.release)
    if not vmlinux:
        res.message = (f"Identifiquei o kernel do dump ({res.release}), mas "
                       "falta o vmlinux com símbolos (kernel-debuginfo).")
        res.steps = symbols_steps(res.release)
        return res
    out_dir = SYMBOLS_DIR / "linux"
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        res.message = f"Não consegui criar {out_dir} ({e})."
        return res
    out_json = out_dir / f"{res.release}.json"
    try:
        with open(out_json, "wb") as f:
            rc = subprocess.run(
                [dwarf2json_path(), "linux", "--elf", vmlinux],
                stdout=f, stderr=subprocess.PIPE, timeout=1800).returncode
    except (OSError, subprocess.SubprocessError) as e:
        _unlink(out_json)
        res.message = f"O dwarf2json falhou ({e})."
        return res
    if rc != 0 or not out_json.is_file() or out_json.stat().st_size == 0:
        _unlink(out_json)
        res.message = "O dwarf2json não gerou os símbolos (vmlinux sem DWARF?)."
        return res
    res.ok = True
    res.isf_path = str(out_json)
    res.message = (f"Símbolos gerados para {res.release}. Clique em Analisar de "
                   "novo — agora deve funcionar.")
    return res


def _unlink(p: Path) -> None:
    try:
        p.unlink()
    except OSError:
        pass
