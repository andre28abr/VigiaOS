"""Registro de módulos do VigiaBlue (blue team / SOC / defesa).

Esqueleto: nomes, ícones, categorias e o que cada módulo vai integrar. Vários
módulos aproveitam o core do Activity Log (Rust), que já tem potencial de
SIEM-lite. Os backends entram depois, módulo a módulo.
"""

from __future__ import annotations

from vigia_common.shell import Dependency, Module, ProductMeta

META = ProductMeta(
    key="blue",
    name="VigiaBlue",
    app_id="br.com.vigia.Blue",
    version="0.0.16",
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
        summary="Detecção: regras → alertas triados",
        description="Camada de detecção sobre o core do Activity Log (Rust "
                    "vigia-log): lê os eventos (audit/journald/fail2ban) e "
                    "aplica regras para gerar alertas triados por severidade, "
                    "cada um com explicação leiga e recomendação.",
        wraps=["vigia-log (core)", "regras de detecção"],
        features=["Coleta multi-fonte (audit/journald/fail2ban)",
                  "7 regras de detecção prontas",
                  "Alertas leigos + recomendação + histórico"],
        status="pronto",
        impl="vigia_blue.modules.siem.page",
        requires=(Dependency(
            "vigia-log (core do Activity Log)", ("vigia-log",), "source",
            install="cd tools/activity-log && cargo build --release && "
                    "sudo install -m 0755 target/release/vigia-log /usr/local/bin/",
            note="Mesmo motor do módulo Activity Log do VigiaHub."),),
    ),
    Module(
        id="ids", name="Vigia IDS", category="detection",
        icon="network-wired-symbolic",
        summary="Alertas de intrusão de rede (Suricata)",
        description="Painel para o IDS de rede Suricata: lê o eve.json (de um "
                    "Suricata ativo) ou roda sobre um .pcap, e mostra os "
                    "alertas triados por severidade.",
        wraps=["suricata"],
        features=["Leitura de eve.json (JSONL)", "Análise de .pcap",
                  "Alertas triados + histórico"],
        status="pronto",
        impl="vigia_blue.modules.ids.page",
        requires=(Dependency("Suricata", ("suricata",), "rpm", "suricata"),),
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
        status="pronto",
        impl="vigia_blue.modules.yara.page",
        requires=(Dependency("YARA", ("yara",), "rpm", "yara"),),
    ),
    Module(
        id="memory", name="Vigia Memory", category="forensics",
        icon="media-flash-symbolic",
        summary="Forense de memória (Volatility 3)",
        description="Análise de dumps de memória RAM com o Volatility 3: "
                    "processos, conexões, histórico de comandos e código "
                    "injetado. Analisa um dump existente (não captura a RAM).",
        wraps=["volatility3"],
        features=["11 plugins (Linux + Windows)",
                  "Processos, conexões, bash, malfind", "Resultado em tabela"],
        status="pronto",
        impl="vigia_blue.modules.memory.page",
        requires=(Dependency("Volatility 3", ("vol", "vol.py", "volatility3"),
                             "pip", "volatility3"),),
    ),
    Module(
        id="timeline", name="Vigia Timeline", category="forensics",
        icon="x-office-calendar-symbolic",
        summary="Linha do tempo forense (plaso)",
        description="Super-timeline de eventos do sistema (plaso) para "
                    "reconstruir o que aconteceu e quando. Abre export "
                    "json_line, analisa .plaso ou gera de uma pasta.",
        wraps=["plaso (log2timeline + psort)"],
        features=["Abrir export json_line (sem plaso)",
                  "Gerar de pasta/arquivo ou .plaso",
                  "Eventos em ordem cronológica"],
        status="pronto",
        impl="vigia_blue.modules.timeline.page",
        requires=(Dependency("plaso", ("log2timeline.py", "psort.py",
                                       "log2timeline"), "pip", "plaso"),),
    ),
    Module(
        id="intel", name="Vigia Intel", category="intel",
        icon="applications-internet-symbolic",
        summary="Base local de IOCs + checagem (offline)",
        description="Inteligência de ameaças local (offline-first): mantém uma "
                    "base de IOCs (IPs/domínios/hashes/e-mails maliciosos) e "
                    "checa indicadores contra ela. Importa de texto, OTX e MISP.",
        wraps=["IOCs locais", "OTX", "MISP"],
        features=["Checagem de indicadores offline", "Importação OTX/MISP/texto",
                  "Base local 0600"],
        status="pronto",
        impl="vigia_blue.modules.intel.page",
    ),
    Module(
        id="playbooks", name="Vigia Playbooks", category="response",
        icon="emblem-documents-symbolic",
        summary="Playbooks de resposta a incidentes",
        description="Roteiros guiados de resposta a incidentes (contenção, "
                    "erradicação, recuperação, notificação) com trilha de "
                    "auditoria 0600 — apoio à LGPD art. 48.",
        wraps=["playbooks internos"],
        features=["5 roteiros passo a passo", "Checklist + registro (LGPD)",
                  "Modelos por tipo de incidente"],
        status="pronto",
        impl="vigia_blue.modules.playbooks.page",
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
