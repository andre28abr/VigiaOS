"""Carregamento e renderizacao dos manuais (.md) das tools.

Arquitetura (proposta pelo user 2026-05-28):

  Aba Ajuda no Hub tem 3 sub-abas:
  - Visao geral: ExpanderRows com descricao curta + features (registry)
  - Manual tecnico: detalha comandos, pacotes, paths, arquitetura
  - Manual simples: linguagem leiga, "pra que serve", "quando usar"

Arquivos .md ficam fora do codigo Python pra facilitar edicao:

  docs/manuals/
  ├── tecnico/
  │   ├── _overview.md
  │   ├── vigia-hub.md
  │   ├── activity-log.md
  │   └── ... (17 tools)
  └── leigo/
      ├── _overview.md
      ├── vigia-hub.md
      └── ... (17 tools)

Renderizacao:
- Tenta WebKitGTK 6.0 + python-markdown (HTML rico, suporta tabelas,
  code blocks, imagens, diagramas Mermaid)
- Fallback: Gtk.Label com Pango markup expandido (sem tabelas mas
  funcional em qualquer ambiente)

CSS injetado segue Adwaita color tokens, adapta light/dark.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional


# ============================================================
# Constantes
# ============================================================

ManualKind = Literal["tecnico", "leigo"]
VALID_KINDS: tuple[ManualKind, ...] = ("tecnico", "leigo")

OVERVIEW_ID = "_overview"


# Localizacoes possiveis dos .md (ordem de prioridade):
def manual_dirs() -> list[Path]:
    """Lista paths onde procurar docs/manuals/.

    Em pip install -e (dev): aponta pro repo.
    Em RPM/COPR: /usr/share/vigia-hub/manuals/
    """
    candidates: list[Path] = []

    # 1. Dev mode: relativo ao modulo Python
    # vigia_hub/manuals.py -> tools/vigia-hub/src/vigia_hub/manuals.py
    # repo root = parents[4]
    try:
        module_path = Path(__file__).resolve()
        repo_root = module_path.parents[4]
        dev_path = repo_root / "docs" / "manuals"
        if dev_path.is_dir():
            candidates.append(dev_path)
    except (IndexError, OSError):
        pass

    # 2. Sistema (RPM install)
    for sys_path in [
        Path("/usr/share/vigia-hub/manuals"),
        Path("/usr/local/share/vigia-hub/manuals"),
        Path.home() / ".local" / "share" / "vigia-hub" / "manuals",
    ]:
        if sys_path.is_dir():
            candidates.append(sys_path)

    return candidates


def find_manual_path(tool_id: str, kind: ManualKind) -> Optional[Path]:
    """Acha o arquivo .md correspondente. Retorna None se nao existe."""
    for base in manual_dirs():
        p = base / kind / f"{tool_id}.md"
        if p.is_file():
            return p
    return None


def load_manual(tool_id: str, kind: ManualKind) -> str:
    """Le o .md. Retorna placeholder se nao encontrar."""
    path = find_manual_path(tool_id, kind)
    if path is None:
        return _placeholder_manual(tool_id, kind)
    try:
        return path.read_text(encoding="utf-8")
    except OSError as e:
        return f"# Erro ao ler manual\n\n```\n{e}\n```"


def _placeholder_manual(tool_id: str, kind: ManualKind) -> str:
    """Conteudo padrao quando o .md nao existe ainda."""
    kind_label = "técnico" if kind == "tecnico" else "simples"
    return (
        f"# {tool_id}\n\n"
        f"## Manual {kind_label} em preparação\n\n"
        "Este manual ainda não foi escrito. Veja a aba **Visão geral** "
        "para uma descrição rápida desta ferramenta.\n\n"
        "Para contribuir, edite o arquivo:\n\n"
        f"```\ndocs/manuals/{kind}/{tool_id}.md\n```\n"
    )


# ============================================================
# Detecao de libs
# ============================================================


def webkit_available() -> bool:
    """True se gi WebKit 6.0 esta disponivel."""
    try:
        import gi
        gi.require_version("WebKit", "6.0")
        from gi.repository import WebKit  # noqa: F401
        return True
    except (ValueError, ImportError):
        return False


def markdown_lib_available() -> bool:
    """True se python-markdown esta instalado."""
    try:
        import markdown  # noqa: F401
        return True
    except ImportError:
        return False


# ============================================================
# CSS Adwaita-aware (light/dark)
# ============================================================


CSS_TEMPLATE = """
:root {
    --bg: #fafafa;
    --fg: #2e3436;
    --fg-dim: #57606a;
    --accent: #1c71d8;
    --code-bg: #f6f8fa;
    --pre-bg: #f6f8fa;
    --border: #d0d7de;
    --table-stripe: #f6f8fa;
    --link: #1c71d8;
}
.dark {
    --bg: #1e1e1e;
    --fg: #e3e3e3;
    --fg-dim: #99a1a8;
    --accent: #62a0ea;
    --code-bg: #2d2d2d;
    --pre-bg: #2d2d2d;
    --border: #3d3d3d;
    --table-stripe: #2a2a2a;
    --link: #62a0ea;
}
* { box-sizing: border-box; }
html, body {
    margin: 0; padding: 0;
    background: var(--bg);
    color: var(--fg);
    font-family: -gtk-system, "Cantarell", "Segoe UI", system-ui, sans-serif;
    font-size: 14px;
    line-height: 1.55;
}
.container {
    max-width: 760px;
    margin: 0 auto;
    padding: 28px 40px 60px;
}
h1, h2, h3, h4 {
    color: var(--fg);
    margin-top: 1.6em;
    margin-bottom: 0.6em;
    font-weight: 600;
}
h1 {
    font-size: 1.9em;
    margin-top: 0;
    padding-bottom: 0.3em;
    border-bottom: 1px solid var(--border);
}
h2 {
    font-size: 1.4em;
    color: var(--accent);
    padding-bottom: 0.2em;
    border-bottom: 1px solid var(--border);
}
h3 { font-size: 1.15em; }
h4 { font-size: 1.0em; color: var(--fg-dim); }
p { margin: 0.8em 0; }
a { color: var(--link); text-decoration: none; }
a:hover { text-decoration: underline; }
ul, ol { padding-left: 1.6em; margin: 0.6em 0; }
li { margin: 0.3em 0; }
code {
    background: var(--code-bg);
    padding: 2px 5px;
    border-radius: 4px;
    font-family: "Source Code Pro", "JetBrains Mono", monospace;
    font-size: 0.92em;
    color: var(--accent);
}
pre {
    background: var(--pre-bg);
    padding: 14px 18px;
    border-radius: 8px;
    border: 1px solid var(--border);
    overflow-x: auto;
    font-size: 0.9em;
    line-height: 1.45;
    margin: 1em 0;
}
pre code {
    background: transparent;
    padding: 0;
    color: var(--fg);
    font-size: inherit;
}
table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
}
th, td {
    border: 1px solid var(--border);
    padding: 8px 12px;
    text-align: left;
}
th {
    background: var(--table-stripe);
    font-weight: 600;
}
tr:nth-child(even) td { background: var(--table-stripe); }
blockquote {
    border-left: 4px solid var(--accent);
    background: var(--code-bg);
    padding: 0.6em 1em;
    margin: 1em 0;
    color: var(--fg-dim);
    border-radius: 0 6px 6px 0;
}
hr {
    border: none;
    border-top: 1px solid var(--border);
    margin: 2em 0;
}
.kbd, kbd {
    background: var(--code-bg);
    border: 1px solid var(--border);
    border-bottom-width: 2px;
    border-radius: 4px;
    padding: 1px 6px;
    font-family: monospace;
    font-size: 0.85em;
}
"""


def build_html(markdown_text: str, dark_mode: bool = False) -> str:
    """Renderiza markdown -> HTML completo com CSS embutido.

    Se python-markdown nao esta disponivel, encapsula o texto bruto
    num <pre> (melhor que mostrar markdown raw).
    """
    if markdown_lib_available():
        import markdown
        body = markdown.markdown(
            markdown_text,
            extensions=[
                "extra",       # tables, fenced_code, footnotes, etc
                "sane_lists",
                "smarty",      # smart quotes
            ],
            output_format="html5",
        )
    else:
        # Fallback: mostra raw com formatacao minima
        import html as html_lib
        escaped = html_lib.escape(markdown_text)
        body = f"<pre style='white-space: pre-wrap;'>{escaped}</pre>"

    body_class = "dark" if dark_mode else ""
    return (
        "<!DOCTYPE html>\n"
        "<html>\n<head>\n"
        '<meta charset="utf-8">\n'
        "<style>"
        + CSS_TEMPLATE
        + "</style>\n"
        "</head>\n"
        f'<body class="{body_class}">\n'
        '<div class="container">\n'
        + body
        + "\n</div>\n</body>\n</html>"
    )


# ============================================================
# Catalogo de tools mostradas no manual
# ============================================================


@dataclass
class ManualEntry:
    """Entrada do sumario de manuais (sidebar)."""
    tool_id: str       # id usado nos arquivos .md (matches docs/manuals/<kind>/<id>.md)
    name: str          # nome humano pra sidebar
    icon_name: str = "application-x-executable-symbolic"


# Lista fixa de entries. Inclui pseudo-entry _overview no topo.
# IDs devem corresponder aos arquivos .md em docs/manuals/<kind>/.
MANUAL_ENTRIES: list[ManualEntry] = [
    ManualEntry("_overview", "Visão geral da Suite", "view-list-symbolic"),
    ManualEntry("vigia-hub", "Vigia Hub", "view-grid-symbolic"),
    ManualEntry("activity-log", "Activity Log", "view-list-bullet-symbolic"),
    ManualEntry("dashboard", "Dashboard", "speedometer-symbolic"),
    ManualEntry("privacy-controls", "Privacy Controls", "system-lock-screen-symbolic"),
    ManualEntry("selinux-gui", "SELinux Manager", "security-high-symbolic"),
    ManualEntry("firewall-gui", "Firewall Manager", "network-wired-symbolic"),
    ManualEntry("netmon-gui", "Network Monitor", "network-transmit-receive-symbolic"),
    ManualEntry("hardening-checks", "Hardening Checks", "emblem-default-symbolic"),
    ManualEntry("reports", "Reports", "document-edit-symbolic"),
    ManualEntry("file-integrity", "File Integrity", "drive-harddisk-symbolic"),
    ManualEntry("tool-installer", "Tool Installer", "package-x-generic-symbolic"),
    ManualEntry("dns-manager", "DNS Manager", "network-server-symbolic"),
    ManualEntry("capabilities-inspector", "Capabilities Inspector", "preferences-system-symbolic"),
    ManualEntry("antivirus", "Antivirus", "security-medium-symbolic"),
    ManualEntry("rootkit-scanner", "Rootkit Scanner", "dialog-warning-symbolic"),
    ManualEntry("deployments-manager", "Deployments Manager", "drive-multidisk-symbolic"),
]
