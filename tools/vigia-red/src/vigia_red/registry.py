"""Registro de módulos do VigiaRed (pentest / red team).

7 módulos, todos prontos e com backend puro + GUI (`Module.impl`): recon,
netscan, vuln, web, wireless, exploit, cracker. Todos passam pelo termo de uso
na 1ª execução (Lei 12.737/2012) — uso só em sistemas próprios/autorizados.
"""

from __future__ import annotations

from vigia_common.shell import Dependency, Module, ProductMeta

META = ProductMeta(
    key="red",
    name="VigiaRed",
    app_id="br.com.vigia.Red",
    version="0.7.0",
    tagline=(
        "Suíte ofensiva (pentest / red team) com interface gráfica moderna — "
        "parte do ecossistema VigiaOS. 7 módulos, todos atrás de termo de uso."
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
            "theHarvester",
            install="pipx install git+https://github.com/laramies/theHarvester.git",
            note="OSINT passivo de fontes abertas. Requer Python 3."),),
    ),
    Module(
        id="netscan", name="Vigia Network Scanner", category="recon",
        icon="network-wired-symbolic",
        summary="Descoberta de portas e serviços (nmap)",
        description="Varredura ATIVA com nmap: portas abertas e serviço/versão "
                    "de um alvo autorizado. Complementa o Vigia Recon (passivo).",
        wraps=["nmap"],
        features=["9 perfis (Top/Web/SYN/UDP/Agressiva/ping sweep…) + portas custom",
                  "Scripts NSE — inclui detecção de vulnerabilidades",
                  "Modo admin (SYN/UDP/SO via pkexec)",
                  "Detecção de SO + relatório 0600 por alvo"],
        status="pronto",
        impl="vigia_red.modules.netscan.page",
        requires=(Dependency("nmap", ("nmap",), "rpm", "nmap",
                  note="Varredura de portas/serviços. Roda sem root (TCP connect)."),),
    ),
    Module(
        id="vuln", name="Vigia Vuln Scanner", category="scanning",
        icon="security-medium-symbolic",
        summary="Varredura de vulnerabilidades por templates",
        description="Aprofunda o que o Network Scanner achou: roda templates do "
                    "nuclei (CVEs, exposições, configs) contra um alvo autorizado "
                    "e classifica por severidade.",
        wraps=["nuclei"],
        features=["Templates nuclei (CVE / exposição / config)",
                  "5 perfis por severidade e tags",
                  "Achados ordenados por gravidade",
                  "Cancelar + exportar laudo (0600)"],
        status="pronto",
        impl="vigia_red.modules.vuln.page",
        requires=(Dependency(
            "nuclei", ("nuclei",), "source", "nuclei",
            install="go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
            note="Scanner de vulns por templates. Requer Go (sudo dnf install golang)."),),
    ),
    Module(
        id="web", name="Vigia Web Scanner", category="web",
        icon="applications-internet-symbolic",
        summary="Vulnerabilidades de aplicações web (wapiti)",
        description="Rastreia uma aplicação web autorizada e testa falhas estilo "
                    "OWASP (XSS, SQLi, inclusão de arquivo…). Complementa o Vuln "
                    "Scanner no nível da aplicação.",
        wraps=["wapiti"],
        features=["Crawler + testes OWASP (XSS/SQLi/…)",
                  "Perfis por escopo (página/pasta/domínio)",
                  "Achados por severidade", "Cancelar + exportar laudo (0600)"],
        status="pronto",
        impl="vigia_red.modules.web.page",
        requires=(Dependency(
            "wapiti", ("wapiti",), "pip", "wapiti3",
            install="pipx install wapiti3",
            note="Scanner de vulns web (OWASP). Requer Python 3."),),
    ),
    Module(
        id="wireless", name="Vigia Wireless", category="wireless",
        icon="network-wireless-symbolic",
        summary="Robustez da senha da SUA rede Wi-Fi",
        description="Auditoria da SUA própria rede sem fio: testa se a senha do "
                    "Wi-Fi resiste a um ataque de dicionário sobre um handshake "
                    "capturado. Responde 'minha senha aguenta?', não serve para "
                    "acessar rede alheia (Lei 12.737/2012).",
        wraps=["aircrack-ng"],
        features=["Testa handshake WPA/WPA2 contra wordlist",
                  "Monta o passo de captura (airodump-ng) — documentado",
                  "Relatório 0600 (sem salvar a senha em claro no histórico)"],
        status="pronto",
        impl="vigia_red.modules.wireless.page",
        requires=(Dependency(
            "aircrack-ng", ("aircrack-ng",), "rpm", "aircrack-ng",
            note="Suíte de auditoria Wi-Fi. A CAPTURA do handshake exige placa "
                 "em modo monitor + root; o TESTE só precisa do .cap."),),
    ),
    Module(
        id="exploit", name="Vigia Exploit", category="exploit",
        icon="utilities-terminal-symbolic",
        summary="Explorador educacional do Metasploit",
        description="Aprenda como um framework de exploração é organizado: busca "
                    "e informação de módulos do Metasploit, e geração de payload "
                    "para praticar contra um alvo de LABORATÓRIO seu (ex.: "
                    "Metasploitable). Não embute payload em executável real nem "
                    "evade antivírus — é para estudo.",
        wraps=["metasploit-framework"],
        features=["Busca e info de módulos (não toca em alvo)",
                  "Geração de payload de laboratório (msfvenom, 0600)",
                  "Enquadrado em alvos próprios/de treino (Lei 12.737/2012)"],
        status="pronto",
        impl="vigia_red.modules.exploit.page",
        requires=(Dependency(
            "metasploit-framework", ("msfconsole", "msfvenom"), "source",
            "metasploit-framework",
            install="curl https://raw.githubusercontent.com/rapid7/"
                    "metasploit-omnibus/master/config/templates/"
                    "metasploit-framework-wrappers/msfupdate.erb > /tmp/msfinstall "
                    "&& chmod +x /tmp/msfinstall && sudo /tmp/msfinstall",
            note="Framework de exploração (grande, ~1 GB). Instalador oficial "
                 "Rapid7 — não está nos repositórios padrão do Fedora."),),
    ),
    Module(
        id="cracker", name="Vigia Cracker", category="password",
        icon="dialog-password-symbolic",
        summary="Robustez de senhas/hashes (auditoria)",
        description="Auditoria DEFENSIVA de senhas: dado um arquivo de hashes que "
                    "VOCÊ já possui (ex.: /etc/shadow do seu servidor), testa "
                    "quais senhas são fracas o bastante para cair num ataque de "
                    "dicionário — para exigir a troca delas.",
        wraps=["john", "hashcat"],
        features=["Ataque por dicionário (+ regras) com john ou hashcat",
                  "Catálogo de tipos de hash comuns (MD5→sha512crypt, NTLM…)",
                  "Relatório 0600 (guarda só o identificador do hash fraco)"],
        status="pronto",
        impl="vigia_red.modules.cracker.page",
        requires=(Dependency(
            "John the Ripper (ou hashcat)", ("john", "hashcat"), "rpm", "john",
            note="john roda em CPU (sem setup). hashcat usa GPU (mais rápido) — "
                 "instale com: sudo dnf install hashcat."),),
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
