"""Backend `getcap`.

- scan_binaries_user() — getcap -r em paths comuns, sem pkexec (limitado)
- scan_binaries_elevated() — `pkexec getcap -r /usr /opt /var` (cobertura total)
- get_caps_for_path(path) — caps de um binario especifico
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field


# Paths comuns onde caps tipicamente estao.
# Excluimos /proc, /sys, /dev, /run (nao tem binarios).
SCAN_PATHS = ["/usr/bin", "/usr/sbin", "/usr/libexec", "/usr/local/bin", "/usr/local/sbin", "/opt"]
SCAN_PATHS_FULL = ["/usr", "/opt", "/var", "/srv"]


@dataclass
class BinaryWithCaps:
    path: str
    capabilities: list[str] = field(default_factory=list)  # ex: ["cap_net_raw=ep"]

    @property
    def cap_names(self) -> list[str]:
        """Nomes das capabilities sem o flags suffix (=ep, =eip, etc)."""
        names: list[str] = []
        for cap in self.capabilities:
            # 'cap_net_admin,cap_net_raw=ep' -> ['cap_net_admin', 'cap_net_raw']
            base = cap.split("=", 1)[0]
            for name in base.split(","):
                name = name.strip()
                if name and name not in names:
                    names.append(name)
        return names


# ============================================================
# Sanity
# ============================================================


def getcap_available() -> bool:
    return shutil.which("getcap") is not None


def _run(cmd: list[str], timeout: int = 60) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 1, "", ""


# ============================================================
# Parsing
# ============================================================


_GETCAP_LINE_RE = re.compile(r"^(.+?)\s+([a-zA-Z_,=+\-]+)$")


def parse_getcap_output(text: str) -> list[BinaryWithCaps]:
    """Parseia output do getcap -r.

    Formato:
      /usr/bin/ping cap_net_raw=ep
      /usr/sbin/arping cap_net_raw=ep
      /usr/bin/example cap_net_admin,cap_net_raw=ep
    """
    binaries: list[BinaryWithCaps] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Pula linhas de erro do getcap ("not permitted", "such file", etc.)
        if line.startswith("getcap:") or "Operation not permitted" in line:
            continue

        m = _GETCAP_LINE_RE.match(line)
        if not m:
            continue

        path = m.group(1).strip()
        caps_str = m.group(2).strip()
        if not caps_str:
            continue

        binaries.append(BinaryWithCaps(path=path, capabilities=[caps_str]))

    return binaries


# ============================================================
# Scan (sem pkexec, paths comuns)
# ============================================================


def scan_binaries_user() -> list[BinaryWithCaps]:
    """Scan limitado, sem pkexec. So pega o que o user pode ler."""
    if not getcap_available():
        return []

    results: list[BinaryWithCaps] = []
    for path in SCAN_PATHS:
        rc, out, _ = _run(["getcap", "-r", path], timeout=30)
        if rc == 0 and out:
            results.extend(parse_getcap_output(out))

    # Dedupe por path
    seen: set[str] = set()
    deduped: list[BinaryWithCaps] = []
    for b in results:
        if b.path not in seen:
            seen.add(b.path)
            deduped.append(b)
    return deduped


# ============================================================
# Scan elevated (pkexec, cobertura total)
# ============================================================


def scan_binaries_elevated() -> tuple[list[BinaryWithCaps], str]:
    """Scan completo via pkexec. UM dialog cobre todos os paths."""
    if not getcap_available():
        return [], "getcap nao instalado (pacote libcap)."

    # set +e: getcap retorna 1 quando encontra paths sem caps; nao queremos abortar
    paths_str = " ".join(SCAN_PATHS_FULL)
    script = f"""set +e
for path in {paths_str}; do
    [ -d "$path" ] && getcap -r "$path" 2>/dev/null
done
exit 0
"""
    rc, out, err = _run(["pkexec", "bash", "-c", script], timeout=120)
    if rc in (126, 127):
        return [], "Autenticacao cancelada."
    if rc != 0 and not out:
        return [], (err.strip() or "Falha no scan.")

    return parse_getcap_output(out), ""


def get_caps_for_path(path: str) -> tuple[list[str], str]:
    """Caps de um binario especifico. Funciona como user se o binario for legivel."""
    if not getcap_available():
        return [], "getcap nao disponivel."

    rc, out, err = _run(["getcap", path], timeout=5)
    if rc != 0:
        return [], (err or "Sem capabilities ou path inacessivel.")
    out = out.strip()
    if not out:
        return [], "Sem capabilities."
    # Formato: '/path cap_net_raw=ep'
    parts = out.split(None, 1)
    if len(parts) < 2:
        return [], ""
    return [parts[1]], ""
