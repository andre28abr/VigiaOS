"""Geração do relatório HTML do VigiaOS — PURO (sem GTK), testável.

Recebe o resumo (`vigia_common.events.summary`) + uma lista de eventos (objetos
com `.ts/.source/.severity/.title/.ref`) e devolve um HTML imprimível com **selo
SHA-256** do conteúdo (integridade — mesmo padrão do Vigia Reports). Os rótulos
de severidade/fonte ficam aqui pra a GUI reusar.
"""

from __future__ import annotations

import hashlib
import html as _html
from datetime import datetime

from vigia_common import events

# severidade canônica -> (rótulo PT, classe-css)
SEV = {
    "critical": ("Crítico", "error"),
    "high": ("Alto", "error"),
    "medium": ("Médio", "warning"),
    "low": ("Baixo", "accent"),
    "info": ("Informativo", "dim-label"),
    "ok": ("OK", "success"),
    "unknown": ("Outro", "dim-label"),
}

# fonte (id da ferramenta) -> rótulo amigável
SOURCE_LABEL = {
    "antivirus": "Antivírus", "rootkit": "Rootkit Scanner",
    "vuln": "Vuln Scanner", "netscan": "Network Scanner", "recon": "Recon",
    "hardening": "Hardening", "posture": "Tudo Certo?",
}


def sev_label(s: object) -> tuple[str, str]:
    return SEV.get(str(s or "").lower(), ("Outro", "dim-label"))


def src_label(s: object) -> str:
    return SOURCE_LABEL.get(str(s or ""), str(s or ""))


_CSS = """
body { font-family: system-ui, -apple-system, sans-serif; color:#1d1d1f;
       max-width:900px; margin:2rem auto; padding:0 1rem; }
h1 { margin:0 0 .2rem; }
h2 { border-bottom:2px solid #1a8c4c; padding-bottom:.2rem; margin-top:1.6rem; }
.meta { color:#555; }
table { width:100%; border-collapse:collapse; font-size:.9rem; }
th,td { text-align:left; padding:.4rem .5rem; border-bottom:1px solid #ddd;
        vertical-align:top; }
th { background:#f3f4f6; }
.pill { display:inline-block; background:#eef; border-radius:10px;
        padding:.1rem .5rem; margin:.1rem; font-size:.85rem; }
.error { color:#b3261e; font-weight:600; }
.warning { color:#9a6700; font-weight:600; }
.success { color:#1a8c4c; } .accent { color:#1a73e8; } .dim-label { color:#777; }
footer { margin-top:2rem; color:#888; font-size:.8rem; border-top:1px solid #ddd;
         padding-top:.5rem; word-break:break-all; }
@media print { body { margin:0; max-width:none; } }
"""


def build_html(period_label: str, summary: dict, evs, *, generated=None) -> str:
    """Monta o relatório HTML imprimível com selo SHA-256 no rodapé.

    `generated` (datetime) é injetável pra teste determinístico.
    """
    gen = (generated or datetime.now()).strftime("%d/%m/%Y %H:%M")
    summary = summary or {}
    by_sev = summary.get("by_severity", {}) or {}
    by_src = summary.get("by_source", {}) or {}

    sev_cells = "".join(
        f"<span class='pill {sev_label(s)[1]}'>{sev_label(s)[0]}: {by_sev[s]}</span> "
        for s in events.CANON_SEVERITIES if by_sev.get(s))
    src_cells = "".join(
        f"<span class='pill'>{_html.escape(src_label(s))}: {n}</span> "
        for s, n in sorted(by_src.items(), key=lambda kv: -kv[1]))

    rows = "".join(
        "<tr>"
        f"<td>{_html.escape(str(e.ts))}</td>"
        f"<td>{_html.escape(src_label(e.source))}</td>"
        f"<td class='{sev_label(e.severity)[1]}'>{sev_label(e.severity)[0]}</td>"
        f"<td>{_html.escape(str(e.title))}</td>"
        f"<td>{_html.escape(str(e.ref))}</td>"
        "</tr>"
        for e in (evs or []))

    body = f"""<header>
  <h1>Relatório de Segurança — VigiaOS</h1>
  <p class="meta">Período: <b>{_html.escape(period_label)}</b> ·
     Gerado em {gen} · Total: <b>{summary.get('total', 0)}</b> evento(s)</p>
</header>
<section>
  <h2>Resumo</h2>
  <p>Por severidade: {sev_cells or '—'}</p>
  <p>Por ferramenta: {src_cells or '—'}</p>
</section>
<section>
  <h2>Eventos</h2>
  <table>
    <thead><tr><th>Quando</th><th>Ferramenta</th><th>Severidade</th>
      <th>Evento</th><th>Onde</th></tr></thead>
    <tbody>{rows or '<tr><td colspan="5">Nenhum evento no período.</td></tr>'}</tbody>
  </table>
</section>"""

    seal = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>Relatório VigiaOS — {_html.escape(period_label)}</title>
<style>{_CSS}</style></head>
<body>{body}
<footer>Selo de integridade (SHA-256 do conteúdo):<br>{seal}</footer>
</body></html>"""
