"""Renderer Jinja2 → HTML.

Templates em vigia_reports/templates/ sao carregados via PackageLoader.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import socket
import zipfile
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from . import __version__, charts, config


# Mapping id -> arquivo de template
TEMPLATES: dict[str, dict] = {
    "activity_overview": {
        "name": "Atividade geral",
        "description": "Resumo do que aconteceu no período (SSH, sudo, fail2ban, logins). Bom para revisão mensal.",
        "file": "activity_overview.html",
    },
    "auth_events": {
        "name": "Eventos de autenticação",
        "description": "Detalhamento de logins SSH, sudo, pkexec, logins falhados. Bom para auditoria LGPD.",
        "file": "auth_events.html",
    },
    "executive_summary": {
        "name": "Resumo executivo",
        "description": "Uma página visual com o panorama do período — ideal para cliente, auditor ou arquivo mensal.",
        "file": "executive_summary.html",
    },
    "admin_access": {
        "name": "Acesso administrativo",
        "description": "Trilha de comandos com privilégio (sudo + pkexec): quem rodou o quê, quando. Foco LGPD.",
        "file": "admin_access.html",
    },
    "lgpd_compliance": {
        "name": "Conformidade LGPD",
        "description": "Postura de segurança/privacidade da máquina agora (firewall, disco cifrado, DNS, telemetria…) — o documento para o auditor.",
        "file": "lgpd_compliance.html",
    },
    "system_health": {
        "name": "Saúde do sistema",
        "description": "Consolida o último resultado de Hardening (Lynis), Antivírus, Integridade (AIDE) e Rootkits num só documento.",
        "file": "system_health.html",
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
    env = Environment(
        loader=PackageLoader("vigia_reports", "templates"),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    # Geradores de grafico SVG disponiveis nos templates (usar com | safe).
    env.globals["bar_chart"] = charts.bar_chart
    env.globals["hbar_chart"] = charts.hbar_chart
    env.globals["donut"] = charts.donut
    return env


def _doc_seal(ctx: dict) -> str:
    """SHA-256 do conteúdo (dados + metadata) — selo visível no rodapé.

    Fingerprint determinístico do que foi coletado nesta geração (inclui o
    `generated_at`, então é único por documento). Não é o hash do arquivo —
    para verificação independente do arquivo use o sidecar `.sha256`.
    """
    def _default(o):
        if isinstance(o, datetime):
            return o.isoformat()
        return str(o)

    try:
        blob = json.dumps(ctx, sort_keys=True, ensure_ascii=False, default=_default)
    except (TypeError, ValueError):
        blob = repr(ctx)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def render_html(template_id: str, data: dict) -> str:
    if template_id not in TEMPLATES:
        raise ValueError(f"Template desconhecido: {template_id}")

    env = _make_env()
    template = env.get_template(TEMPLATES[template_id]["file"])

    ctx = dict(data)
    ctx["meta"] = system_metadata()
    ctx["report_name"] = TEMPLATES[template_id]["name"]
    ctx["org"] = config.org_context()  # identidade do escritório (cabeçalho/rodapé)
    ctx["doc_seal"] = _doc_seal(ctx)  # selo cobre conteúdo + org, computado por último
    return template.render(**ctx)


def write_report(html: str, template_id: str, output_dir: Path) -> Path:
    """Salva HTML em output_dir/<template>-<timestamp>.html, retorna o path.

    LGPD: relatorios contem IPs, comandos sudo, historico de login (lastb).
    Em sistema multi-user ou shared NFS, defaults 0644 expoem isso para
    outros usuarios. Forcamos 0600 (owner read/write apenas) no arquivo
    e 0700 no diretorio.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    # mkdir nao define mode (chmod nao roda se ja existir). Forcamos:
    try:
        output_dir.chmod(0o700)
    except OSError:
        pass

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{template_id}-{stamp}.html"
    path = output_dir / filename
    path.write_text(html, encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass

    # Sidecar de integridade: SHA-256 do ARQUIVO, formato `sha256sum`.
    # write_text(utf-8) grava exatamente html.encode("utf-8"), então este
    # digest bate com `sha256sum <file>` → verificável com `sha256sum -c`.
    try:
        digest = hashlib.sha256(html.encode("utf-8")).hexdigest()
        sidecar = path.with_name(path.name + ".sha256")
        sidecar.write_text(f"{digest}  {path.name}\n", encoding="utf-8")
        sidecar.chmod(0o600)
    except OSError:
        pass
    return path


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_audit_package(reports_dir: Path) -> tuple[Path | None, int, str]:
    """Empacota relatórios .html + sidecars + manifesto num `.zip` (0600).

    O zip é um artefato de auditoria entregável: os relatórios, os `.sha256`
    (verificáveis com `sha256sum -c`), um `MANIFEST.txt` com todos os hashes e
    um `LEIA-ME.txt` com o passo a passo. Retorna `(zip_path, n, erro)`.
    """
    if not reports_dir.is_dir():
        return None, 0, "A pasta de relatórios ainda não existe."
    htmls = sorted(reports_dir.glob("*.html"), key=lambda p: p.stat().st_mtime)
    if not htmls:
        return None, 0, "Nenhum relatório para empacotar — gere ao menos um."

    entries: list[tuple[Path, str]] = []
    for h in htmls:
        try:
            entries.append((h, _sha256_file(h)))
        except OSError:
            continue
    if not entries:
        return None, 0, "Não foi possível ler os relatórios."

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    zip_path = reports_dir / f"auditoria-{stamp}.zip"
    oldest = datetime.fromtimestamp(entries[0][0].stat().st_mtime)
    newest = datetime.fromtimestamp(entries[-1][0].stat().st_mtime)

    manifest = [
        "PACOTE DE AUDITORIA — VigiaOS Reports",
        f"Gerado em : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Host      : {socket.gethostname()}",
        f"Periodo   : {oldest.strftime('%Y-%m-%d')} a {newest.strftime('%Y-%m-%d')}",
        f"Relatorios: {len(entries)}",
        "",
        "SHA-256                                                            arquivo",
        "-" * 80,
    ]
    for h, digest in entries:
        manifest.append(f"{digest}  {h.name}")

    readme = (
        "PACOTE DE AUDITORIA — VigiaOS\n"
        "=============================\n\n"
        "Este .zip reune os relatorios de seguranca gerados e seus selos de\n"
        "integridade, para entrega a auditor / arquivamento (LGPD).\n\n"
        "Como conferir que nenhum relatorio foi adulterado:\n"
        "  1. Extraia este arquivo .zip.\n"
        "  2. Num terminal, na pasta extraida, rode:\n"
        "         sha256sum -c *.sha256\n"
        "     Cada relatorio deve responder 'OK'. Um 'FAILED' indica que o\n"
        "     arquivo foi alterado depois de gerado.\n\n"
        "Todos os hashes tambem estao em MANIFEST.txt.\n"
    )

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for h, digest in entries:
                zf.write(h, h.name)
                sidecar = h.with_name(h.name + ".sha256")
                if sidecar.is_file():
                    zf.write(sidecar, sidecar.name)
                else:
                    zf.writestr(f"{h.name}.sha256", f"{digest}  {h.name}\n")
            zf.writestr("MANIFEST.txt", "\n".join(manifest) + "\n")
            zf.writestr("LEIA-ME.txt", readme)
        os.chmod(zip_path, 0o600)
    except OSError as e:
        return None, 0, f"Falha ao criar o pacote: {e}"

    return zip_path, len(entries), ""
