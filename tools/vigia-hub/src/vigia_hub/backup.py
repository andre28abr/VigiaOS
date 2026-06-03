"""Backup / restauracao das configuracoes e dados do VigiaOS (.zip).

LGPD: o .zip pode conter relatorios de scan (caminhos de arquivos do
usuario, achados etc.) — dado sensivel. Por isso:
- o arquivo e' criado com permissao **0600** (so o dono le/escreve);
- na restauracao, os arquivos voltam a 0600 e os diretorios a 0700.

Estrutura do .zip:
    MANIFEST.json
    config/<vigia-dir>/...    -> restaura em ~/.config/<vigia-dir>
    data/<vigia-dir>/...      -> restaura em ~/.local/share/<vigia-dir>

Seguranca na restauracao (anti Zip-Slip): cada entrada precisa
- nao ser caminho absoluto;
- nao conter componente '..';
- comecar com 'config/' ou 'data/';
- ter o segmento de diretorio comecando com 'vigia'.
Qualquer entrada fora disso faz a restauracao ABORTAR (nao extrai nada
de um arquivo suspeito).

PURO PYTHON (sem GTK) — testavel e usavel pela CLI `vigia`.
"""

from __future__ import annotations

import json
import os
import socket
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import __version__


CONFIG_HOME = Path.home() / ".config"
DATA_HOME = Path.home() / ".local" / "share"
BACKUP_DIR = DATA_HOME / "vigia-hub" / "backups"

# (label, kind, dirname). kind: "config" -> ~/.config ; "data" -> ~/.local/share
#
# NOTA: NAO incluimos `data/vigia-hub` de proposito — ele contem o cache
# de manuais (re-baixavel) e a propria pasta `backups/` (evita backup
# recursivo de backups). So as settings do Hub (config/vigia-hub) entram.
_SOURCES: list[tuple[str, str, str]] = [
    ("Configurações do Hub", "config", "vigia-hub"),
    ("Alertas e integridade", "config", "vigia"),
    ("Tool Installer", "config", "vigia-installer"),
    ("Antivírus (relatórios)", "data", "vigia-antivirus"),
    ("Hashes (baselines)", "data", "vigia-hash"),
    ("Relatórios LGPD", "data", "vigia-reports"),
    ("Rootkit (scans)", "data", "vigia-rootkit"),
]


@dataclass
class BackupSource:
    label: str
    kind: str       # "config" | "data"
    dirname: str
    src: Path


# ============================================================
# Helpers internos
# ============================================================


def _base_for(kind: str) -> Path:
    return CONFIG_HOME if kind == "config" else DATA_HOME


def _label_for(kind: str, dirname: str) -> str:
    for label, k, d in _SOURCES:
        if k == kind and d == dirname:
            return label
    return f"{kind}/{dirname}"


def default_backup_name() -> str:
    """Nome sugerido pro arquivo de backup."""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"vigia-backup-{ts}.zip"


# ============================================================
# Backup
# ============================================================


def backup_sources() -> list[BackupSource]:
    """Lista as fontes de backup que EXISTEM no sistema agora."""
    out: list[BackupSource] = []
    for label, kind, dirname in _SOURCES:
        src = _base_for(kind) / dirname
        if src.is_dir():
            out.append(BackupSource(label, kind, dirname, src))
    return out


def create_backup(dest: Path | None = None) -> tuple[bool, str, Path | None]:
    """Cria um .zip (0600) com config + dados da suite.

    Args:
        dest: caminho do .zip. None -> BACKUP_DIR/vigia-backup-<ts>.zip.

    Returns:
        (ok, mensagem, caminho_do_zip | None)
    """
    sources = backup_sources()
    if not sources:
        return (False, "Nada para backup — nenhum dado da Vigia encontrado.", None)

    if dest is None:
        try:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            os.chmod(BACKUP_DIR, 0o700)
        except OSError as e:
            return (False, f"Não foi possível criar a pasta de backups: {e}", None)
        dest = BACKUP_DIR / default_backup_name()
    else:
        dest = Path(dest)
        if dest.suffix.lower() != ".zip":
            dest = dest.with_name(dest.name + ".zip")
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return (False, f"Pasta de destino inválida: {e}", None)

    manifest = {
        "format": "vigia-backup",
        "schema": 1,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "hostname": socket.gethostname(),
        "hub_version": __version__,
        "contents": [
            {"label": s.label, "kind": s.kind, "dir": s.dirname} for s in sources
        ],
    }

    tmp = dest.parent / (dest.name + ".tmp")
    file_count = 0
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "MANIFEST.json",
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )
            for s in sources:
                for path in sorted(s.src.rglob("*")):
                    if path.is_file() and not path.is_symlink():
                        rel = path.relative_to(s.src).as_posix()
                        arcname = f"{s.kind}/{s.dirname}/{rel}"
                        zf.write(path, arcname)
                        file_count += 1
        os.chmod(tmp, 0o600)
        tmp.replace(dest)
        os.chmod(dest, 0o600)
    except (OSError, zipfile.BadZipFile) as e:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        return (False, f"Falha ao criar backup: {e}", None)

    return (True, f"Backup criado com {file_count} arquivo(s).", dest)


def list_backups(limit: int = 20) -> list[dict]:
    """Lista backups recentes em BACKUP_DIR (mais novo primeiro)."""
    if not BACKUP_DIR.is_dir():
        return []
    try:
        files = sorted(
            BACKUP_DIR.glob("vigia-backup-*.zip"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return []
    out: list[dict] = []
    for f in files[:limit]:
        try:
            st = f.stat()
        except OSError:
            continue
        out.append({
            "path": str(f),
            "name": f.name,
            "size": st.st_size,
            "mtime": st.st_mtime,
        })
    return out


# ============================================================
# Restore
# ============================================================


def _is_safe_member(name: str) -> bool:
    """True se a entrada do zip e' segura pra extrair (anti Zip-Slip)."""
    if not name or name.endswith("/"):
        return False
    if name.startswith("/") or name.startswith("\\"):
        return False
    # Normaliza separadores e quebra em componentes
    parts = name.replace("\\", "/").split("/")
    if any(p in ("", ".", "..") for p in parts):
        return False
    if len(parts) < 3:
        return False
    kind, dirname = parts[0], parts[1]
    if kind not in ("config", "data"):
        return False
    if not dirname.startswith("vigia"):
        return False
    return True


def _target_path(name: str) -> Path:
    parts = name.replace("\\", "/").split("/")
    kind = parts[0]
    rest = parts[1:]
    return _base_for(kind).joinpath(*rest)


def _tighten_perms(roots: set[tuple[str, str]]) -> None:
    """Diretorios restaurados -> 0700 (best effort)."""
    for kind, dirname in roots:
        top = _base_for(kind) / dirname
        if not top.is_dir():
            continue
        try:
            os.chmod(top, 0o700)
            for sub in top.rglob("*"):
                try:
                    if sub.is_dir():
                        os.chmod(sub, 0o700)
                except OSError:
                    pass
        except OSError:
            pass


def restore_backup(
    zip_path: Path,
    *,
    dry_run: bool = False,
) -> tuple[bool, str, list[str]]:
    """Restaura config + dados de um backup .zip da Vigia.

    Args:
        zip_path: caminho do .zip.
        dry_run: se True, apenas reporta o que seria restaurado (nao escreve).

    Returns:
        (ok, mensagem, labels_restaurados)
    """
    zip_path = Path(zip_path)
    if not zip_path.is_file():
        return (False, "Arquivo de backup não encontrado.", [])

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            try:
                names = zf.namelist()
            except zipfile.BadZipFile:
                return (False, "Arquivo .zip inválido ou corrompido.", [])

            if "MANIFEST.json" not in names:
                return (
                    False,
                    "Não parece um backup da Vigia (sem MANIFEST.json).",
                    [],
                )

            members: list[str] = []
            for name in names:
                if name == "MANIFEST.json" or name.endswith("/"):
                    continue
                if not _is_safe_member(name):
                    return (
                        False,
                        f"Backup recusado por segurança (entrada suspeita): {name}",
                        [],
                    )
                members.append(name)

            roots: set[tuple[str, str]] = set()
            for name in members:
                parts = name.replace("\\", "/").split("/")
                roots.add((parts[0], parts[1]))

            labels = sorted({_label_for(k, d) for (k, d) in roots})

            if dry_run:
                return (
                    True,
                    f"{len(members)} arquivo(s) seriam restaurados.",
                    labels,
                )

            for name in members:
                target = _target_path(name)
                try:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(name) as src, open(target, "wb") as dst:
                        dst.write(src.read())
                    os.chmod(target, 0o600)
                except OSError as e:
                    return (False, f"Falha ao restaurar {name}: {e}", [])

            _tighten_perms(roots)
            return (
                True,
                f"{len(members)} arquivo(s) restaurados.",
                labels,
            )
    except (OSError, zipfile.BadZipFile) as e:
        return (False, f"Falha ao restaurar: {e}", [])
