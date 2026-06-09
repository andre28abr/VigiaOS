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
  │   └── ... (16 tools + _overview)
  └── leigo/
      ├── _overview.md
      ├── vigia-hub.md
      └── ... (16 tools + _overview)

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
    /* Light mode — alto contraste, fundo branco puro pra legibilidade
       em VMs com resolucao reduzida (UTM/QEMU) */
    --bg: #ffffff;
    --fg: #1d1d1f;
    --fg-dim: #4a4a52;
    --accent: #1a8c4c;       /* Adwaita green 6 — identidade visual Vigia */
    --accent-dim: #26a269;   /* Adwaita green 5 */
    --code-bg: #f3f4f6;
    --code-fg: #b04a00;      /* marrom-laranja: nao compete com accent */
    --pre-bg: #f6f8fa;
    --border: #d0d7de;
    --table-stripe: #f3f4f6;
    --link: #1a8c4c;
    --quote-bg: #e8f5ee;     /* verde palido pra blockquote */
}
.dark {
    /* Dark mode — Adwaita 1.5+ tones */
    --bg: #242424;
    --fg: #ffffff;
    --fg-dim: #beb6b6;
    --accent: #57e389;       /* Adwaita green 4 — vivo no dark */
    --accent-dim: #33d17a;
    --code-bg: #303030;
    --code-fg: #ff9050;
    --pre-bg: #1e1e1e;
    --border: #454545;
    --table-stripe: #2a2a2a;
    --link: #57e389;
    --quote-bg: #1d3527;
}

/* Anti-aliasing forte — corrige texto "lavado" em VM */
html {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
    font-feature-settings: "kern" 1, "liga" 1;
}

* { box-sizing: border-box; }

html, body {
    margin: 0; padding: 0;
    background: var(--bg);
    color: var(--fg);
    font-family: "Cantarell", "Inter", -apple-system, BlinkMacSystemFont,
                 "Segoe UI", "Helvetica Neue", system-ui, sans-serif;
    font-size: 15px;
    line-height: 1.6;
    font-weight: 400;
}
.container {
    max-width: 780px;
    margin: 0 auto;
    padding: 32px 44px 80px;
}

/* Headings */
h1, h2, h3, h4 {
    color: var(--fg);
    margin-top: 1.6em;
    margin-bottom: 0.5em;
    font-weight: 700;
    letter-spacing: -0.01em;
}
h1 {
    font-size: 2em;
    margin-top: 0;
    padding-bottom: 0.35em;
    border-bottom: 2px solid var(--accent);
    color: var(--accent);
}
h2 {
    font-size: 1.45em;
    color: var(--accent);
    padding-bottom: 0.25em;
    border-bottom: 1px solid var(--border);
    margin-top: 2em;
}
h3 {
    font-size: 1.2em;
    color: var(--fg);
    font-weight: 600;
}
h4 {
    font-size: 1.0em;
    color: var(--fg-dim);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

/* Paragraphs / lists / links */
p { margin: 0.9em 0; }
a {
    color: var(--link);
    text-decoration: none;
    font-weight: 500;
}
a:hover { text-decoration: underline; }

ul, ol { padding-left: 1.7em; margin: 0.7em 0; }
li { margin: 0.35em 0; }

strong, b { font-weight: 700; color: var(--fg); }
em, i { font-style: italic; }

/* Inline code — marrom/laranja pra nao competir com accent verde */
code {
    background: var(--code-bg);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: "JetBrains Mono", "Source Code Pro", "Cascadia Code",
                 "DejaVu Sans Mono", monospace;
    font-size: 0.88em;
    color: var(--code-fg);
    font-weight: 500;
}

/* Block code */
pre {
    background: var(--pre-bg);
    padding: 16px 20px;
    border-radius: 8px;
    border: 1px solid var(--border);
    overflow-x: auto;
    font-size: 0.88em;
    line-height: 1.5;
    margin: 1.2em 0;
}
pre code {
    background: transparent;
    padding: 0;
    color: var(--fg);
    font-size: inherit;
    font-weight: 400;
}

/* Tables */
table {
    border-collapse: collapse;
    width: 100%;
    margin: 1.2em 0;
    font-size: 0.95em;
}
th, td {
    border: 1px solid var(--border);
    padding: 9px 14px;
    text-align: left;
}
th {
    background: var(--table-stripe);
    font-weight: 700;
    color: var(--fg);
}
tr:nth-child(even) td { background: var(--table-stripe); }

/* Blockquote — verde palido coerente com accent */
blockquote {
    border-left: 4px solid var(--accent);
    background: var(--quote-bg);
    padding: 0.8em 1.2em;
    margin: 1.2em 0;
    color: var(--fg);
    border-radius: 0 6px 6px 0;
}
blockquote p { margin: 0.4em 0; }

hr {
    border: none;
    border-top: 1px solid var(--border);
    margin: 2.2em 0;
}

kbd {
    background: var(--code-bg);
    border: 1px solid var(--border);
    border-bottom-width: 2px;
    border-radius: 4px;
    padding: 1px 6px;
    font-family: monospace;
    font-size: 0.85em;
    color: var(--fg);
}

/* Scrollbar styling pra integrar visualmente */
::-webkit-scrollbar { width: 12px; height: 12px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb {
    background: var(--border);
    border-radius: 6px;
    border: 2px solid var(--bg);
}
::-webkit-scrollbar-thumb:hover { background: var(--fg-dim); }
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
    ManualEntry("checkup", "Tudo Certo?", "security-high-symbolic"),
    ManualEntry("vigia-hub", "Vigia Hub", "view-grid-symbolic"),
    ManualEntry("activity-log", "Activity Log", "view-list-bullet-symbolic"),
    ManualEntry("dashboard", "Dashboard", "applications-utilities-symbolic"),
    ManualEntry("privacy-controls", "Privacy Controls", "system-lock-screen-symbolic"),
    ManualEntry("selinux-gui", "SELinux Manager", "security-high-symbolic"),
    ManualEntry("firewall-gui", "Firewall Manager", "network-wired-symbolic"),
    ManualEntry("netmon-gui", "Network Monitor", "network-transmit-receive-symbolic"),
    ManualEntry("hardening-checks", "Hardening Checks", "applications-system-symbolic"),
    ManualEntry("reports", "Reports", "document-edit-symbolic"),
    ManualEntry("file-integrity", "File Integrity", "drive-harddisk-symbolic"),
    ManualEntry("tool-installer", "Atualizações", "software-update-available-symbolic"),
    ManualEntry("dns-manager", "DNS Manager", "network-server-symbolic"),
    ManualEntry("capabilities-inspector", "Capabilities Inspector", "preferences-system-symbolic"),
    ManualEntry("antivirus", "Antivirus", "security-medium-symbolic"),
    ManualEntry("rootkit-scanner", "Rootkit Scanner", "dialog-warning-symbolic"),
]
