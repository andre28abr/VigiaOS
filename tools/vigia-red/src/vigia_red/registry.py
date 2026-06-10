"""Registro de módulos do VigiaRed (pentest / red team).

Esqueleto: nomes, ícones, categorias e o que cada módulo vai integrar. Os
backends entram depois, módulo a módulo, com termo de uso na 1ª execução
(Lei 12.737/2012).
"""

from __future__ import annotations

from vigia_common.shell import Dependency, Module, ProductMeta

META = ProductMeta(
    key="red",
    name="VigiaRed",
    app_id="br.com.vigia.Red",
    version="0.1.0",
    tagline=(
        "Suíte ofensiva (pentest / red team) com interface gráfica moderna — "
        "parte do ecossistema VigiaOS. Esqueleto: os módulos chegam um a um."
    ),
    accent="#ef4444",
    audience="Pentester, red team, security researcher.",
    legal_notice=(
        "Uso restrito a sistemas próprios ou com autorização formal por "
        "escrito. Acesso não autorizado a dispositivos é crime no Brasil "
        "(Lei 12.737/2012). Cada módulo do VigiaRed exibirá um termo de uso "
        "na primeira execução."
    ),
)

CATEGORIES = {
    "recon": "Reconhecimento & OSINT",
    "scanning": "Varredura & Vulnerabilidades",
    "web": "Aplicações Web",
    "wireless": "Wireless",
    "exploit": "Exploração",
    "password": "Senhas & Hashes",
}
ORDER = ["recon", "scanning", "web", "wireless", "exploit", "password"]

MODULES: list[Module] = [
    Module(
        id="recon", name="Vigia Recon", category="recon",
        icon="system-search-symbolic",
        summary="OSINT — e-mails, subdomínios, hosts",
        description="Coleta passiva de inteligência de fontes abertas (OSINT) "
                    "para mapear a superfície externa de um alvo autorizado.",
        wraps=["theHarvester"],
        features=["Enumeração de subdomínios e hosts",
                  "Coleta de e-mails e credenciais expostas",
                  "Mapa da superfície externa (relatório 0600)"],
        status="pronto",
        impl="vigia_red.modules.recon.page",
        requires=(Dependency(
            "theHarvester", ("theHarvester", "theharvester"), "pip",
            "theHarvester", install="pipx install theHarvester",
            note="OSINT passivo de fontes abertas. Requer Python 3."),),
    ),
    Module(
        id="netscan", name="Vigia Network Scanner", category="recon",
        icon="network-wired-symbolic",
        summary="Descoberta de portas e serviços (nmap)",
        description="Varredura de rede com nmap: hosts vivos, portas abertas, "
                    "fingerprint de serviço e versão. (Voltou ao produto certo "
                    "— foi tirado do VigiaHub por não ser de escritório/LGPD.)",
        wraps=["nmap"],
        features=["Descoberta de hosts e portas", "Detecção de serviço/versão",
                  "Scripts NSE selecionados", "Saída salva por alvo"],
    ),
    Module(
        id="vuln", name="Vigia Vuln Scanner", category="scanning",
        icon="security-medium-symbolic",
        summary="Varredura de vulnerabilidades por templates",
        description="Identifica vulnerabilidades conhecidas via templates "
                    "comunitários atualizáveis.",
        wraps=["nuclei", "nikto"],
        features=["Templates nuclei atualizáveis", "Checagens web (nikto)",
                  "Severidade + referência CVE"],
    ),
    Module(
        id="web", name="Vigia Web Scanner", category="web",
        icon="applications-internet-symbolic",
        summary="Scanner de aplicações web (ZAP)",
        description="Análise dinâmica de aplicações web: spider, fuzzing de "
                    "parâmetros e detecção de falhas OWASP Top 10.",
        wraps=["OWASP ZAP", "wapiti"],
        features=["Spider + scan ativo/passivo", "Top 10 OWASP",
                  "Proxy de interceptação"],
    ),
    Module(
        id="wireless", name="Vigia Wireless", category="wireless",
        icon="network-wireless-symbolic",
        summary="Auditoria de redes Wi-Fi",
        description="Auditoria de segurança de redes sem fio próprias: captura "
                    "de handshake e teste de robustez de senha.",
        wraps=["aircrack-ng", "wifite"],
        features=["Captura de handshake WPA/WPA2", "Teste de força de senha",
                  "Inventário de redes ao alcance"],
    ),
    Module(
        id="exploit", name="Vigia Exploit", category="exploit",
        icon="utilities-terminal-symbolic",
        summary="Framework de exploração (Metasploit)",
        description="Front-end gráfico leve para seleção de módulos, payloads "
                    "e sessões do Metasploit Framework.",
        wraps=["metasploit-framework"],
        features=["Busca de módulos/exploits", "Geração de payload",
                  "Gestão de sessões"],
    ),
    Module(
        id="cracker", name="Vigia Cracker", category="password",
        icon="dialog-password-symbolic",
        summary="Auditoria de senhas e hashes",
        description="Teste de robustez de hashes/senhas com wordlists e regras "
                    "(auditoria autorizada).",
        wraps=["hashcat", "john"],
        features=["Ataque por dicionário e regras", "GPU (hashcat)",
                  "Identificação de tipo de hash"],
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
