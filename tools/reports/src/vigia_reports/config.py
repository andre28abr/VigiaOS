"""Identidade do escritório nos relatórios (nome, logo, responsável).

Persistida em `~/.config/vigia/reports.json` (0600). Injetada no cabeçalho e
rodapé de todo relatório, transformando a saída genérica num documento do
escritório. O logo vira um data-URI base64 (o relatório fica self-contained —
o logo viaja junto ao ser enviado por e-mail).
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "vigia"
CONFIG_FILE = CONFIG_DIR / "reports.json"

_DEFAULTS = {"org_name": "", "org_subtitle": "", "responsible": "", "logo_path": ""}

_MIME = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".svg": "image/svg+xml", ".webp": "image/webp",
}
_LOGO_MAX_BYTES = 512 * 1024  # 512 KB — evita relatório gigante


def load_config() -> dict:
    cfg = dict(_DEFAULTS)
    if CONFIG_FILE.is_file():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        if isinstance(data, dict):
            for k in _DEFAULTS:
                if isinstance(data.get(k), str):
                    cfg[k] = data[k]
    return cfg


def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(CONFIG_DIR, 0o700)
    except OSError:
        pass
    clean = {k: str(cfg.get(k, "")) for k in _DEFAULTS}
    try:
        CONFIG_FILE.write_text(
            json.dumps(clean, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        os.chmod(CONFIG_FILE, 0o600)
    except OSError:
        pass


def logo_data_uri(path: str) -> str:
    """Imagem → `data:` URI base64. "" se vazio/inexistente/inválido/grande.

    Suporta PNG/JPG/GIF/SVG/WebP, até 512 KB (relatório self-contained).
    """
    if not path:
        return ""
    p = Path(path)
    mime = _MIME.get(p.suffix.lower())
    if mime is None:
        return ""
    try:
        if p.stat().st_size > _LOGO_MAX_BYTES:
            return ""
        raw = p.read_bytes()
    except OSError:
        return ""
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


def org_context() -> dict:
    """Dict pronto pro template Jinja: name / subtitle / responsible / logo_uri."""
    cfg = load_config()
    return {
        "name": cfg["org_name"].strip(),
        "subtitle": cfg["org_subtitle"].strip(),
        "responsible": cfg["responsible"].strip(),
        "logo_uri": logo_data_uri(cfg["logo_path"]),
    }
