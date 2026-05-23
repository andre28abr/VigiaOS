"""Renderer Jinja2 → HTML.

Templates em vigia_reports/templates/ sao carregados via PackageLoader.
"""

from __future__ import annotations

import platform
import socket
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from . import __version__


# Mapping id -> arquivo de template
TEMPLATES: dict[str, dict] = {
    "activity_overview": {
        "name": "Atividade geral",
        "description": "Resumo do que aconteceu no periodo (SSH, sudo, fail2ban, logins). Bom para revisao mensal.",
        "file": "activity_overview.html",
    },
    "auth_events": {
        "name": "Eventos de autenticacao",
        "description": "Detalhamento de logins SSH, sudo, pkexec, logins falhados. Bom para auditoria LGPD.",
        "file": "auth_events.html",
    },
}


def list_templates() -> list[tuple[str, str, str]]:
    """Retorna [(id, name, description)] para popular UI."""
    return [(tid, t["name"], t["description"]) for tid, t in TEMPLATES.items()]


def get_template_name(template_id: str) -> str:
    return TEMPLATES.get(template_id, {}).get("name", template_id)


def system_metadata() -> dict:
    """Metadados do sistema para o footer dos relatorios."""
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = "unknown"
    return {
        "hostname": hostname,
        "platform": platform.platform(),
        "vigia_version": __version__,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _make_env() -> Environment:
    return Environment(
        loader=PackageLoader("vigia_reports", "templates"),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_html(template_id: str, data: dict) -> str:
    if template_id not in TEMPLATES:
        raise ValueError(f"Template desconhecido: {template_id}")

    env = _make_env()
    template = env.get_template(TEMPLATES[template_id]["file"])

    ctx = dict(data)
    ctx["meta"] = system_metadata()
    ctx["report_name"] = TEMPLATES[template_id]["name"]
    return template.render(**ctx)


def write_report(html: str, template_id: str, output_dir: Path) -> Path:
    """Salva HTML em output_dir/<template>-<timestamp>.html, retorna o path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{template_id}-{stamp}.html"
    path = output_dir / filename
    path.write_text(html, encoding="utf-8")
    return path
