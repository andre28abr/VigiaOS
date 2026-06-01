"""Backend do Vigia YARA — caça a malware por regras YARA.

Wrapper do CLI `yara`, no mesmo padrão dos scanners do VigiaHub (Antivírus/
Rootkit Scanner): escaneia um path com um conjunto de regras → parseia os
matches → lista de achados → salva relatório JSON (0600) + histórico.

Partes PURAS (testáveis headless, sem `yara` instalado):
- `parse_yara_output(text)` — parser da saída do `yara`.
- `build_scan_cmd(...)` — monta o argv (lista, nunca shell — convenção do projeto).
- `list_rules(dir)` / `bundled_rules` — descoberta de regras.

Parte que toca o sistema:
- `scan(...)` — roda via `vigia_common.proc.run` (nunca levanta) + salva relatório.

Formato da saída do `yara` (1 linha por match):
    RuleName /caminho/arquivo
    RuleName [tag1,tag2] /caminho/arquivo     (com -g)
Linhas de strings casadas (`-s`) começam com offset hex (`0x...`) — ignoradas.
"""

from __future__ import annotations

import re
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from vigia_common import proc
from vigia_common.state import load_json, save_json_0600

# ~/.local/share/vigia-yara/{rules,scan-*.json}
DATA_DIR = Path.home() / ".local" / "share" / "vigia-yara"
RULES_DIR = DATA_DIR / "rules"
REPORTS_DIR = DATA_DIR

# Regras de partida empacotadas no produto (EICAR + heurística de webshell).
_BUNDLED_RULES_DIR = Path(__file__).resolve().parents[4] / "data" / "yara-rules"


@dataclass
class Match:
    """Um match do YARA: a regra que disparou e o arquivo onde."""

    rule: str
    path: str
    tags: list[str] = field(default_factory=list)


@dataclass
class ScanResult:
    target: str
    matches: list[Match] = field(default_factory=list)
    rules_count: int = 0
    elapsed_sec: float = 0.0
    error: str = ""
    started_at: str = ""        # ISO timestamp


# ============================================================
# Sanity / descoberta de regras
# ============================================================


def yara_available() -> bool:
    return shutil.which("yara") is not None


def yara_version() -> str:
    rc, out, _ = proc.run(["yara", "--version"], timeout=5)
    return out.strip() if rc == 0 else ""


def list_rules(rules_dir: Path | str = RULES_DIR) -> list[Path]:
    """Arquivos de regra (.yar/.yara) num diretório, ordenados."""
    d = Path(rules_dir)
    if not d.is_dir():
        return []
    found = list(d.glob("*.yar")) + list(d.glob("*.yara"))
    return sorted(found)


def bundled_rules() -> list[Path]:
    """Regras de partida que vêm com o produto (EICAR + webshell heurística)."""
    return list_rules(_BUNDLED_RULES_DIR)


def effective_rules() -> list[Path]:
    """Regras do usuário (RULES_DIR) se existirem; senão as empacotadas."""
    user = list_rules(RULES_DIR)
    return user or bundled_rules()


# ============================================================
# Parser (puro)
# ============================================================

# rule name = identificador C (sem espaços); path absoluto começa com '/'.
_TAGS_RE = re.compile(r"^\[(?P<tags>[\w,\-]*)\]\s*(?P<rest>.+)$")


def parse_yara_output(text: str) -> list[Match]:
    """Parseia a saída do `yara`. Cada match vira um `Match(rule, path, tags)`.

    Ignora linhas vazias, de erro/aviso e as de strings casadas (`-s`, que
    começam com offset hex `0x...` ou vêm indentadas).
    """
    matches: list[Match] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        # linhas de strings casadas (-s) ou indentadas
        if line[0].isspace() or line.lstrip().startswith("0x"):
            continue
        low = line.lower()
        if low.startswith(("error", "warning", "yara:")):
            continue

        parts = line.split(None, 1)
        if len(parts) < 2:
            continue
        rule, rest = parts[0], parts[1].strip()

        tags: list[str] = []
        m = _TAGS_RE.match(rest)
        if m:  # forma "rule [tags] path"
            tags = [t for t in m.group("tags").split(",") if t]
            rest = m.group("rest").strip()

        if not rest:
            continue
        matches.append(Match(rule=rule, path=rest, tags=tags))
    return matches


# ============================================================
# Command builder (puro)
# ============================================================


def build_scan_cmd(
    rules: list[Path | str], target: Path | str, recursive: bool = True
) -> list[str]:
    """Monta o argv do `yara` (lista — nunca shell string).

    `yara [-r] [-w] REGRA... ALVO`. Múltiplos arquivos de regra são permitidos
    antes do alvo. `-w` silencia warnings de regra (reduz ruído no parse).

    NÃO usamos `--`: o parser do `yara` não o reconhece como fim-de-opções —
    tentaria abrir `--` como arquivo de regra ("could not open file: --").
    Segurança vem de passar argv em LISTA (sem shell); o alvo chega absoluto
    (`/...`) do seletor, então não é confundido com opção.
    """
    cmd = ["yara", "-w"]
    if recursive:
        cmd.append("-r")
    cmd.extend(str(r) for r in rules)
    cmd.append(str(target))
    return cmd


# ============================================================
# Scan (toca o sistema via proc.run)
# ============================================================


def scan(
    target: Path | str,
    rules: list[Path | str] | None = None,
    recursive: bool = True,
    timeout: int = 900,
) -> ScanResult:
    """Escaneia `target` com `rules` (default: effective_rules()). Nunca levanta."""
    if rules is None:
        rules = effective_rules()  # type: ignore[assignment]
    rules = list(rules or [])

    result = ScanResult(
        target=str(target),
        started_at=datetime.now().isoformat(timespec="seconds"),
        rules_count=len(rules),
    )
    if not rules:
        result.error = "Nenhum conjunto de regras YARA encontrado."
        return result

    t0 = time.monotonic()
    rc, out, err = proc.run(build_scan_cmd(rules, target, recursive), timeout=timeout)
    result.elapsed_sec = round(time.monotonic() - t0, 2)

    result.matches = parse_yara_output(out)
    # yara sai 0 mesmo com matches; rc!=0 sem stdout = erro real (regra inválida,
    # path inacessível, etc.).
    if rc != 0 and not out:
        result.error = (err.strip() or "Falha ao executar o yara.")[:500]
    return result


# ============================================================
# Relatórios (JSON 0600 + histórico) — padrão Antivírus
# ============================================================


def _ensure_reports_dir() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR


def save_report(result: ScanResult) -> Path | None:
    """Salva o resultado em ~/.local/share/vigia-yara/scan-<ts>.json (0600)."""
    if not result.started_at:
        return None
    rd = _ensure_reports_dir()
    safe_ts = result.started_at.replace(":", "-").replace(".", "_")
    path = rd / f"scan-{safe_ts}.json"
    data = {
        "target": result.target,
        "started_at": result.started_at,
        "rules_count": result.rules_count,
        "elapsed_sec": result.elapsed_sec,
        "error": result.error,
        "matches": [{"rule": m.rule, "path": m.path, "tags": m.tags} for m in result.matches],
    }
    return path if save_json_0600(path, data) else None


def list_recent_reports(limit: int = 20) -> list[dict]:
    """Relatórios salvos, mais novos primeiro (descarta corrompidos)."""
    if not REPORTS_DIR.is_dir():
        return []
    files = sorted(
        REPORTS_DIR.glob("scan-*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    out: list[dict] = []
    for f in files[:limit]:
        data = load_json(f)
        if isinstance(data, dict):
            data["_file"] = str(f)
            out.append(data)
    return out
