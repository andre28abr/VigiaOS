"""Backend do Vigia Cracker — auditoria de robustez de senhas/hashes.

Objetivo DEFENSIVO/educacional: dado um arquivo de hashes que VOCÊ já possui
(ex.: o `/etc/shadow` do seu próprio servidor, ou hashes exportados de um banco
seu), testar quais senhas são fracas o suficiente para caírem num ataque de
dicionário. É a mesma coisa que um time de segurança faz para exigir troca das
senhas fracas — não serve para "descobrir a senha de outra pessoa".

Embarca duas ferramentas consagradas: `john` (John the Ripper, roda em CPU, sem
setup) e `hashcat` (usa GPU, mais rápido). O usuário fornece o arquivo de hashes
e uma wordlist (lista de senhas candidatas).

Partes PURAS (testáveis sem john/hashcat, sem GTK):
- `HASH_TYPES` / `find_hash_type` — catálogo de tipos comuns (nome john + modo hashcat).
- `validate_hashfile` / `validate_wordlist` — caminhos existem e são legíveis.
- `build_john_cmd` / `build_john_show_cmd` / `build_hashcat_cmd` / `build_hashcat_show_cmd`.
- `parse_john_show` / `parse_hashcat_show` — saída → (identificador, senha).

Parte que toca o sistema:
- `run_crack(...)` — roda a ferramenta (cancelável) + `--show` + relatório 0600.
"""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from vigia_common import proc
from vigia_common.state import load_json, save_json_0600

from ...runner import ScanProcess

DATA_DIR = Path.home() / ".local" / "share" / "vigia-cracker"
REPORTS_DIR = DATA_DIR


# ============================================================
# Catálogo de tipos de hash (nome no john + modo no hashcat)
# ============================================================


@dataclass(frozen=True)
class HashType:
    id: str
    label: str
    john_format: str      # --format= do john
    hashcat_mode: str     # -m do hashcat
    note: str = ""


# Curado: os tipos que mais aparecem numa auditoria de sistema/aplicação BR.
HASH_TYPES: list[HashType] = [
    HashType("auto", "Detectar automaticamente (john)", "", "",
             "Deixa o john adivinhar o formato. Só funciona com john."),
    HashType("md5", "MD5 (cru)", "raw-md5", "0", "Hash simples, sem sal."),
    HashType("sha1", "SHA-1 (cru)", "raw-sha1", "100", "Hash simples, sem sal."),
    HashType("sha256", "SHA-256 (cru)", "raw-sha256", "1400", ""),
    HashType("sha512", "SHA-512 (cru)", "raw-sha512", "1700", ""),
    HashType("ntlm", "NTLM (Windows)", "nt", "1000",
             "Hash de senha do Windows."),
    HashType("bcrypt", "bcrypt", "bcrypt", "3200",
             "Forte por design — lento de testar."),
    HashType("md5crypt", "md5crypt ($1$)", "md5crypt", "500",
             "Formato antigo de /etc/shadow."),
    HashType("sha256crypt", "sha256crypt ($5$)", "sha256crypt", "7400",
             "/etc/shadow moderno."),
    HashType("sha512crypt", "sha512crypt ($6$)", "sha512crypt", "1800",
             "/etc/shadow padrão no Linux atual."),
]
DEFAULT_HASH_TYPE = "auto"


def find_hash_type(type_id: str) -> HashType | None:
    return next((h for h in HASH_TYPES if h.id == type_id), None)


# ============================================================
# Perfis (estratégia de ataque de dicionário)
# ============================================================


@dataclass(frozen=True)
class Profile:
    id: str
    label: str
    description: str
    use_rules: bool


PROFILES: list[Profile] = [
    Profile("dicionario", "Dicionário",
            "Testa cada palavra da wordlist como está. Rápido.", False),
    Profile("regras", "Dicionário + regras",
            "Aplica variações comuns (Senha→S3nh4!, +ano, etc.). Mais completo, "
            "mais lento.", True),
]
DEFAULT_PROFILE = "dicionario"


# ============================================================
# Engines
# ============================================================

ENGINES = ("john", "hashcat")
DEFAULT_ENGINE = "john"


def john_available() -> bool:
    return shutil.which("john") is not None


def hashcat_available() -> bool:
    return shutil.which("hashcat") is not None


def engine_available(engine: str) -> bool:
    return john_available() if engine == "john" else hashcat_available()


def any_engine_available() -> bool:
    return john_available() or hashcat_available()


# ============================================================
# Resultado
# ============================================================


@dataclass
class Cracked:
    identifier: str    # usuário / índice do hash
    password: str


@dataclass
class CrackResult:
    hashfile: str
    engine: str = ""
    hash_type: str = ""
    profile: str = ""
    cracked: list[Cracked] = field(default_factory=list)
    total_hashes: int = 0
    started_at: str = ""
    elapsed_sec: float = 0.0
    error: str = ""
    ran: bool = False
    raw: str = ""       # saída bruta do --show (export) — não vai no JSON salvo

    @property
    def cracked_count(self) -> int:
        return len(self.cracked)

    @property
    def weak_ratio(self) -> float:
        """Fração de hashes quebrados (= senhas fracas). 0..1."""
        return (self.cracked_count / self.total_hashes) if self.total_hashes else 0.0


# ============================================================
# Validação (puro)
# ============================================================


def _is_readable_file(path: str) -> bool:
    try:
        p = Path(path).expanduser()
        return p.is_file() and p.stat().st_size >= 0
    except OSError:
        return False


def validate_hashfile(path: str) -> bool:
    return bool((path or "").strip()) and _is_readable_file(path)


def validate_wordlist(path: str) -> bool:
    return bool((path or "").strip()) and _is_readable_file(path)


def count_hashes(path: str) -> int:
    """Nº de linhas não vazias no arquivo de hashes. Nunca levanta."""
    try:
        with open(Path(path).expanduser(), encoding="utf-8", errors="replace") as fh:
            return sum(1 for ln in fh if ln.strip())
    except OSError:
        return 0


# ============================================================
# Montadores de comando (puro — argv em lista, nunca shell)
# ============================================================


def build_john_cmd(hashfile: str, wordlist: str, hash_type: str = DEFAULT_HASH_TYPE,
                   use_rules: bool = False) -> list[str]:
    """argv do john para o ataque de dicionário."""
    cmd = ["john", f"--wordlist={wordlist}"]
    ht = find_hash_type(hash_type)
    if ht and ht.john_format:
        cmd.append(f"--format={ht.john_format}")
    if use_rules:
        cmd.append("--rules")
    cmd.append(hashfile)
    return cmd


def build_john_show_cmd(hashfile: str, hash_type: str = DEFAULT_HASH_TYPE) -> list[str]:
    """argv do `john --show` (lista o que já foi quebrado, da pot file)."""
    cmd = ["john", "--show"]
    ht = find_hash_type(hash_type)
    if ht and ht.john_format:
        cmd.append(f"--format={ht.john_format}")
    cmd.append(hashfile)
    return cmd


def build_hashcat_cmd(hashfile: str, wordlist: str, hash_type: str,
                      use_rules: bool = False,
                      rules_path: str = "/usr/share/hashcat/rules/best64.rule") -> list[str]:
    """argv do hashcat para o ataque de dicionário (-a 0 = wordlist)."""
    ht = find_hash_type(hash_type)
    mode = ht.hashcat_mode if (ht and ht.hashcat_mode) else "0"
    cmd = ["hashcat", "-m", mode, "-a", "0", "--quiet", hashfile, wordlist]
    if use_rules:
        cmd += ["-r", rules_path]
    return cmd


def build_hashcat_show_cmd(hashfile: str, hash_type: str) -> list[str]:
    ht = find_hash_type(hash_type)
    mode = ht.hashcat_mode if (ht and ht.hashcat_mode) else "0"
    return ["hashcat", "-m", mode, "--show", hashfile]


# ============================================================
# Parsers (puro) — nunca levantam
# ============================================================


def parse_john_show(text: str) -> list[Cracked]:
    """Parseia `john --show`.

    Formato típico: `usuario:senha:...campos...` por linha, terminando com uma
    linha-resumo tipo `2 password hashes cracked, 3 left`. A senha é o 2º campo.
    """
    out: list[Cracked] = []
    for line in (text or "").splitlines():
        line = line.rstrip("\n")
        if not line.strip():
            continue
        low = line.strip().lower()
        if "password hash" in low and ("cracked" in low or "left" in low):
            continue  # linha-resumo
        if ":" not in line:
            continue
        parts = line.split(":")
        ident = parts[0]
        password = parts[1] if len(parts) > 1 else ""
        out.append(Cracked(identifier=ident, password=password))
    return out


def parse_hashcat_show(text: str) -> list[Cracked]:
    """Parseia `hashcat --show` — linhas `hash:senha` (a senha é tudo após o 1º `:`)."""
    out: list[Cracked] = []
    for line in (text or "").splitlines():
        line = line.rstrip("\n")
        if not line.strip() or ":" not in line:
            continue
        h, _, password = line.partition(":")
        out.append(Cracked(identifier=h[:32], password=password))
    return out


# ============================================================
# Execução (toca o sistema)
# ============================================================


def run_crack(
    hashfile: str,
    wordlist: str,
    *,
    engine: str = DEFAULT_ENGINE,
    hash_type: str = DEFAULT_HASH_TYPE,
    profile_id: str = DEFAULT_PROFILE,
    timeout: int = 1800,
    handle: ScanProcess | None = None,
) -> CrackResult:
    """Roda o ataque de dicionário e lista as senhas fracas. Nunca levanta."""
    res = CrackResult(
        hashfile=hashfile, engine=engine, hash_type=hash_type, profile=profile_id,
        started_at=datetime.now().isoformat(timespec="seconds"),
    )
    if not validate_hashfile(hashfile):
        res.error = "Arquivo de hashes inválido ou ilegível."
        return res
    if not validate_wordlist(wordlist):
        res.error = "Wordlist inválida ou ilegível."
        return res
    if engine not in ENGINES:
        res.error = f"Engine desconhecida: {engine}."
        return res
    if not engine_available(engine):
        res.error = f"{engine} não está instalado."
        return res
    if engine == "hashcat" and hash_type == "auto":
        res.error = ("O hashcat exige o tipo de hash (não tem autodetecção). "
                     "Escolha o tipo, ou use o john.")
        return res

    prof = next((p for p in PROFILES if p.id == profile_id), None)
    use_rules = bool(prof.use_rules) if prof else False
    res.total_hashes = count_hashes(hashfile)

    if engine == "john":
        crack_cmd = build_john_cmd(hashfile, wordlist, hash_type, use_rules)
        show_cmd = build_john_show_cmd(hashfile, hash_type)
        parser = parse_john_show
    else:
        crack_cmd = build_hashcat_cmd(hashfile, wordlist, hash_type, use_rules)
        show_cmd = build_hashcat_show_cmd(hashfile, hash_type)
        parser = parse_hashcat_show

    runner = handle.run if handle is not None else proc.run
    t0 = time.monotonic()
    rc, out, err = runner(crack_cmd, timeout=timeout)
    res.elapsed_sec = round(time.monotonic() - t0, 2)

    # john sai !=0 quando não quebrou nada; hashcat sai 1 = "exhausted". Nenhum
    # dos dois é erro real: quem manda é o `--show`. Só é erro se o show falhar.
    _rc2, show_out, show_err = (handle.run if handle is not None else proc.run)(
        show_cmd, timeout=120)
    res.raw = show_out
    res.cracked = parser(show_out)
    res.ran = True

    # Sinais de erro de verdade (formato errado, ferramenta reclamando).
    blob = (out + "\n" + err + "\n" + show_err).lower()
    if not res.cracked and (
            "unknown ciphertext format" in blob
            or "no hashes loaded" in blob
            or "no such file" in blob
            or "separator unset" in blob):
        res.ran = False
        res.error = _first_meaningful(err) or _first_meaningful(show_err) or (
            "A ferramenta não reconheceu o formato do hash. "
            "Confira o tipo selecionado.")

    save_report(res)
    try:
        from vigia_common import events
        if res.ran and not res.error:
            sev = "high" if res.cracked else "ok"
            events.record(
                "cracker",
                f"Auditoria de senhas: {res.cracked_count} fraca(s) de "
                f"{res.total_hashes}", category="scan", severity=sev,
                ref=Path(hashfile).name,
                payload={"engine": engine, "cracked": res.cracked_count,
                         "total": res.total_hashes})
    except Exception:  # pylint: disable=broad-except
        pass
    return res


def _first_meaningful(text: str) -> str:
    for line in (text or "").splitlines():
        s = line.strip()
        if s and not s.startswith("Warning:"):
            return s[:200]
    return ""


# ============================================================
# Relatórios (JSON 0600 + histórico + export TXT)
# ============================================================


def _ensure_reports_dir() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR


def result_to_dict(r: CrackResult) -> dict:
    return {
        "hashfile": r.hashfile,
        "engine": r.engine,
        "hash_type": r.hash_type,
        "profile": r.profile,
        "started_at": r.started_at,
        "elapsed_sec": r.elapsed_sec,
        "error": r.error,
        "total_hashes": r.total_hashes,
        "cracked_count": r.cracked_count,
        # NÃO salvamos as senhas em claro no relatório de histórico (LGPD /
        # minimização): guardamos só o identificador do hash fraco.
        "weak_identifiers": [c.identifier for c in r.cracked],
    }


def result_to_text(r: CrackResult) -> str:
    lines = [
        f"Vigia Cracker — auditoria de {Path(r.hashfile).name}",
        f"Engine: {r.engine} · tipo: {r.hash_type} · {r.started_at} · "
        f"{r.elapsed_sec:.0f}s",
        "=" * 56,
    ]
    if r.error:
        lines.append(f"Erro: {r.error}")
        return "\n".join(lines) + "\n"
    lines.append(
        f"{r.cracked_count} de {r.total_hashes} hash(es) caíram no dicionário "
        f"({r.weak_ratio * 100:.0f}% de senhas fracas).")
    if r.cracked:
        lines.append("\nSenhas fracas encontradas (troque estas já):")
        for c in r.cracked:
            lines.append(f"  {c.identifier} : {c.password}")
    else:
        lines.append("\nNenhuma senha caiu no dicionário testado. Bom sinal — "
                     "mas isso não prova que todas sejam fortes.")
    return "\n".join(lines) + "\n"


def save_report(result: CrackResult) -> Path | None:
    if not result.started_at:
        return None
    rd = _ensure_reports_dir()
    safe_ts = result.started_at.replace(":", "-").replace(".", "_")
    path = rd / f"cracker-{safe_ts}.json"
    return path if save_json_0600(path, result_to_dict(result)) else None


def _mtime_or_zero(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


def list_recent_reports(limit: int = 20) -> list[dict]:
    if not REPORTS_DIR.is_dir():
        return []
    files = sorted(REPORTS_DIR.glob("cracker-*.json"),
                   key=_mtime_or_zero, reverse=True)
    out: list[dict] = []
    for f in files[:limit]:
        data = load_json(f)
        if isinstance(data, dict):
            data["_file"] = str(f)
            out.append(data)
    return out
