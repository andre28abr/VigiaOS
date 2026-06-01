"""Registro de módulos do VigiaBlue (blue team / SOC / defesa).

Esqueleto: nomes, ícones, categorias e o que cada módulo vai integrar. Vários
módulos aproveitam o core do Activity Log (Rust), que já tem potencial de
SIEM-lite. Os backends entram depois, módulo a módulo.
"""

from __future__ import annotations

from vigia_common.shell import Module, ProductMeta

META = ProductMeta(
    key="blue",
    name="VigiaBlue",
    app_id="br.com.vigia.Blue",
    version="0.0.2",
    tagline=(
        "Suíte defensiva (blue team / SOC) com interface gráfica moderna — "
        "detecção, caça a ameaças, forense e resposta. Parte do ecossistema "
        "VigiaOS. Esqueleto: os módulos chegam um a um."
    ),
    accent="#3b82f6",
    audience="Blue team, analista de SOC, defensor, responder de incidentes.",
)

CATEGORIES = {
    "detection": "Detecção & SIEM",
    "hunting": "Caça a Ameaças",
    "forensics": "Forense",
    "intel": "Threat Intelligence",
    "response": "Resposta a Incidentes",
}
ORDER = ["detection", "hunting", "forensics", "intel", "response"]

MODULES: list[Module] = [
    Module(
        id="siem", name="Vigia SIEM", category="detection",
        icon="view-list-symbolic",
        summary="Agregação + correlação de logs",
        description="SIEM-lite que estende o core do Activity Log (Rust): "
                    "agrega logs de várias fontes, correlaciona eventos e "
                    "gera alertas com regras estilo Sigma.",
        wraps=["vigia-activity-log (core)", "regras Sigma-style"],
        features=["Coleta multi-fonte (audit/journald/fail2ban)",
                  "Correlação + dedupe", "Alertas por regra"],
    ),
    Module(
        id="ids", name="Vigia IDS", category="detection",
        icon="network-wired-symbolic",
        summary="Detecção de intrusão de rede (Suricata/Zeek)",
        description="Painel para IDS de rede: regras, alertas e visão de "
                    "fluxo, sobre Suricata ou Zeek.",
        wraps=["suricata", "zeek"],
        features=["Gestão de regras", "Alertas em tempo real",
                  "Resumo de fluxos de rede"],
    ),
    Module(
        id="yara", name="Vigia YARA", category="hunting",
        icon="system-search-symbolic",
        summary="Caça a malware por regras YARA",
        description="Varredura de arquivos e memória com regras YARA para "
                    "encontrar webshells, miners, droppers e ransomware.",
        wraps=["yara"],
        features=["Conjuntos de regras atualizáveis", "Scan de path e memória",
                  "Quarentena opcional do achado"],
    ),
    Module(
        id="memory", name="Vigia Memory", category="forensics",
        icon="media-flash-symbolic",
        summary="Forense de memória (Volatility 3)",
        description="Análise de dumps de memória RAM: processos, conexões, "
                    "injeções e artefatos de malware.",
        wraps=["volatility3"],
        features=["Lista de processos/conexões do dump",
                  "Detecção de injeção de código", "Extração de artefatos"],
    ),
    Module(
        id="timeline", name="Vigia Timeline", category="forensics",
        icon="x-office-calendar-symbolic",
        summary="Linha do tempo forense (plaso)",
        description="Constrói uma super-timeline de eventos do sistema para "
                    "reconstruir o que aconteceu e quando.",
        wraps=["plaso (log2timeline)"],
        features=["Super-timeline de múltiplas fontes",
                  "Filtro por janela de tempo", "Exportação para análise"],
    ),
    Module(
        id="intel", name="Vigia Intel", category="intel",
        icon="applications-internet-symbolic",
        summary="Feeds de inteligência de ameaças",
        description="Integra feeds de threat intel (IOCs) para enriquecer "
                    "alertas e checar indicadores contra o ambiente.",
        wraps=["MISP", "AlienVault OTX"],
        features=["Importação de IOCs", "Enriquecimento de alertas",
                  "Checagem de indicadores locais"],
    ),
    Module(
        id="playbooks", name="Vigia Playbooks", category="response",
        icon="emblem-documents-symbolic",
        summary="Playbooks de resposta a incidentes",
        description="Roteiros guiados de resposta a incidentes (contenção, "
                    "erradicação, recuperação) com trilha de auditoria.",
        wraps=["playbooks internos"],
        features=["Roteiros passo a passo", "Registro de ações (LGPD)",
                  "Modelos por tipo de incidente"],
    ),
]

# Ícones coloridos (padrão Hub): usa o SVG do módulo em data/modules/<id>.svg
# quando existe; senão mantém o icon-name do tema como fallback.
import dataclasses as _dc
from pathlib import Path as _Path
_ICONS_DIR = _Path(__file__).resolve().parents[2] / "data" / "modules"
MODULES = [
    _dc.replace(_m, icon=str(_p)) if (_p := _ICONS_DIR / f"{_m.id}.svg").is_file() else _m
    for _m in MODULES
]
