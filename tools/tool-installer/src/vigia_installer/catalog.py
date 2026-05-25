"""Catalogo curado de security tools para Fedora Silverblue.

Cada CatalogEntry mapeia um pacote do dnf para uma descricao amigavel
em pt-BR. A ordem dentro de cada categoria importa (mais util primeiro).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CatalogEntry:
    package: str               # nome no dnf (ex: "lynis")
    name: str                  # display name (ex: "Lynis")
    description: str           # 1 linha curta
    why: str                   # por que voce quer isso (1 paragrafo)
    category: str              # auditoria, rede, forense, privacidade, monitoramento
    binary: str = ""           # comando para detectar instalacao (opcional)
    related: list[str] = field(default_factory=list)  # outras tools relacionadas


CATEGORIES_ORDER = [
    "auditoria",
    "rede",
    "monitoramento",
    "privacidade",
    "forense",
]

CATEGORY_LABELS = {
    "auditoria": "Auditoria e hardening",
    "rede": "Rede",
    "monitoramento": "Monitoramento e diagnostico",
    "privacidade": "Privacidade e criptografia",
    "forense": "Forense e analise",
}

CATEGORY_DESCRIPTIONS = {
    "auditoria": "Ferramentas para auditar postura de seguranca, integridade e procurar rootkits.",
    "rede": "Scanners, sniffers e diagnostico de rede.",
    "monitoramento": "O que esta acontecendo no sistema agora — processos, IO, arquivos abertos.",
    "privacidade": "Tor, VPN, DNS encriptado, criptografia.",
    "forense": "Analise pos-incidente, antivirus, hashes e recuperacao.",
}


CATALOG: list[CatalogEntry] = [
    # ===== AUDITORIA ===== #
    CatalogEntry(
        package="lynis",
        name="Lynis",
        description="Auditoria de hardening do sistema (~250 controles).",
        why=(
            "Roda automaticamente checagens de seguranca em **kernel**, **boot**, "
            "**autenticacao**, **firewall**, **MAC**, **logging** e gera um "
            "**Hardening Index** (0–100). Usado pela tool **Vigia Hardening Checks**."
        ),
        category="auditoria",
        binary="lynis",
    ),
    CatalogEntry(
        package="aide",
        name="AIDE",
        description="Monitor de integridade de arquivos (hash baseline + diff).",
        why=(
            "Cria um **snapshot** com hashes SHA256 dos arquivos do sistema. "
            "Detecta quando algo critico foi modificado (`/usr/sbin/sshd`, "
            "`/etc/passwd`, etc.). Usado pela tool **Vigia File Integrity**."
        ),
        category="auditoria",
        binary="aide",
    ),
    CatalogEntry(
        package="chkrootkit",
        name="chkrootkit",
        description="Procura por sinais conhecidos de rootkits.",
        why=(
            "Verifica binarios do sistema contra padroes conhecidos de rootkits "
            "(LKM rootkits, login trojans, etc.). Complementa o AIDE: AIDE diz "
            "*'algo mudou'*, chkrootkit diz *'parece com rootkit X'*."
        ),
        category="auditoria",
        binary="chkrootkit",
    ),
    CatalogEntry(
        package="rkhunter",
        name="Rootkit Hunter",
        description="Outro scanner de rootkits, complementar ao chkrootkit.",
        why=(
            "Mesma ideia do chkrootkit mas com base de assinaturas diferente. "
            "Rodar ambos aumenta cobertura."
        ),
        category="auditoria",
        binary="rkhunter",
    ),

    # ===== REDE ===== #
    CatalogEntry(
        package="nmap",
        name="Nmap",
        description="Scanner de portas e servicos.",
        why=(
            "Padrao da industria para **descobrir hosts** numa rede, **portas "
            "abertas** e **versoes de servicos**. Util para auditar a propria "
            "infra (`nmap localhost` mostra o que esta exposto)."
        ),
        category="rede",
        binary="nmap",
    ),
    CatalogEntry(
        package="tcpdump",
        name="tcpdump",
        description="Captura de pacotes na linha de comando.",
        why=(
            "Quando voce precisa **ver os pacotes** que entram/saem para "
            "debugar algo (`tcpdump -i any port 443`). Mais leve que o "
            "Wireshark mas igualmente potente."
        ),
        category="rede",
        binary="tcpdump",
    ),
    CatalogEntry(
        package="mtr",
        name="MTR",
        description="Traceroute moderno com estatisticas em tempo real.",
        why=(
            "Combina `ping` + `traceroute` em uma interface viva. **A melhor "
            "ferramenta** para descobrir onde a latencia esta na sua rede."
        ),
        category="rede",
        binary="mtr",
    ),
    CatalogEntry(
        package="nethogs",
        name="NetHogs",
        description="Largura de banda por processo (top-like).",
        why=(
            "Mostra **qual processo** esta consumindo banda agora. Util para "
            "achar daemons fofoqueiros ou suspeitar de exfiltracao."
        ),
        category="rede",
        binary="nethogs",
    ),
    CatalogEntry(
        package="iftop",
        name="iftop",
        description="Largura de banda por conexao (host-to-host).",
        why=(
            "Mostra **bandwidth por par origem→destino**. Complementa o "
            "NetHogs: NetHogs e' por processo, iftop e' por conexao."
        ),
        category="rede",
        binary="iftop",
    ),

    # ===== MONITORAMENTO ===== #
    CatalogEntry(
        package="htop",
        name="htop",
        description="Top moderno com cores e arvores de processos.",
        why=(
            "**Substituto melhor do `top`**: barras coloridas de CPU/mem/swap, "
            "tree view, kill com selecao. Use diariamente."
        ),
        category="monitoramento",
        binary="htop",
    ),
    CatalogEntry(
        package="iotop",
        name="iotop",
        description="Top para uso de disco I/O (precisa root).",
        why=(
            "Quando algo esta deixando o disco lento, o iotop mostra **qual "
            "processo** esta gerando o I/O. (`sudo iotop` ou `pkexec iotop`)."
        ),
        category="monitoramento",
        binary="iotop",
    ),
    CatalogEntry(
        package="lsof",
        name="lsof",
        description="Lista arquivos abertos (e sockets) por processo.",
        why=(
            "Resolve perguntas tipo: **quem esta segurando** esse arquivo? "
            "Que processo abriu a porta 8080? (`lsof -i :8080`)."
        ),
        category="monitoramento",
        binary="lsof",
    ),
    CatalogEntry(
        package="strace",
        name="strace",
        description="Tracador de syscalls (debug de processos).",
        why=(
            "Quando um processo trava sem log, `strace -p <pid>` mostra "
            "**em qual syscall** ele esta parado (read, open, futex…). "
            "Ferramenta classica de debug em Linux."
        ),
        category="monitoramento",
        binary="strace",
    ),
    CatalogEntry(
        package="fail2ban",
        name="fail2ban",
        description="Banimento automatico de IPs apos tentativas falhadas.",
        why=(
            "Le os logs de SSH/HTTP/etc e **bane temporariamente IPs** que "
            "tentam brute-force. Configuracao default ja protege SSH. "
            "Eventos aparecem na timeline do **Vigia Activity Log**."
        ),
        category="monitoramento",
        binary="fail2ban-server",
    ),

    # ===== PRIVACIDADE ===== #
    CatalogEntry(
        package="tor",
        name="Tor",
        description="Daemon do Tor (proxy de anonimato).",
        why=(
            "Roda como servico local na porta `9050` (SOCKS5). Apos instalar: "
            "`systemctl enable --now tor` e configure aplicacoes para usar o "
            "proxy. **Vigia Privacy Controls** tem toggle para iniciar/parar."
        ),
        category="privacidade",
        binary="tor",
    ),
    CatalogEntry(
        package="torsocks",
        name="torsocks",
        description="Wrapper para rodar comandos atraves do Tor.",
        why=(
            "`torsocks curl https://example.com` envia a request via Tor sem "
            "precisar configurar proxy manualmente. Util para tests pontuais."
        ),
        category="privacidade",
        binary="torsocks",
    ),
    CatalogEntry(
        package="wireguard-tools",
        name="WireGuard",
        description="VPN moderna e simples (chave publica/privada).",
        why=(
            "VPN **muito mais simples e rapida** que OpenVPN. Config em "
            "arquivo `.conf` curto. O Vigia VPN Manager (futuro) vai usar "
            "esta ferramenta como base."
        ),
        category="privacidade",
        binary="wg",
    ),
    CatalogEntry(
        package="dnscrypt-proxy",
        name="dnscrypt-proxy",
        description="DNS over HTTPS/TLS local.",
        why=(
            "**Encripta as queries DNS** que normalmente vao em texto puro. "
            "Roda como servico local que substitui o resolver default. "
            "O Vigia DNS Manager (futuro) vai gerenciar este servico."
        ),
        category="privacidade",
        binary="dnscrypt-proxy",
    ),

    # ===== FORENSE ===== #
    CatalogEntry(
        package="clamav",
        name="ClamAV",
        description="Antivirus open-source com base de assinaturas grande.",
        why=(
            "Apesar de Linux ter poucos virus *para Linux*, ClamAV e' util "
            "para **escanear anexos de email** e **arquivos compartilhados** "
            "que vao para Windows. Apos instalar, `freshclam` atualiza a DB."
        ),
        category="forense",
        binary="clamscan",
    ),
    # NOTA: ClamTK removido do catalogo. O Vigia vai criar GUI propria
    # para o ClamAV (planejada: "Vigia Antivirus" — usa clamav como backend).
    # Manter ClamTK aqui duplicaria o caso de uso. O clamav (pacote)
    # continua no catalogo pra que a futura tool Vigia possa usar.
    CatalogEntry(
        package="binwalk",
        name="binwalk",
        description="Extrator e analisador de firmwares/imagens binarias.",
        why=(
            "Util para **analisar firmwares de IoT** ou descobrir o que esta "
            "embutido em arquivos binarios (assinaturas, arquivos comprimidos, "
            "filesystem images embedded)."
        ),
        category="forense",
        binary="binwalk",
    ),
    CatalogEntry(
        package="hashdeep",
        name="hashdeep",
        description="Computa hashes recursivamente + compara conjuntos.",
        why=(
            "Quando voce quer hashear uma pasta inteira e depois verificar se "
            "**algum arquivo mudou** sem precisar de baseline AIDE. Util para "
            "cadeia de custodia em casos forenses."
        ),
        category="forense",
        binary="hashdeep",
    ),
]


def by_category() -> dict[str, list[CatalogEntry]]:
    """Retorna {category: [entries]} preservando ordem do catalogo."""
    out: dict[str, list[CatalogEntry]] = {}
    for entry in CATALOG:
        out.setdefault(entry.category, []).append(entry)
    # Reordena baseado em CATEGORIES_ORDER
    return {c: out[c] for c in CATEGORIES_ORDER if c in out}


def find_by_package(package: str) -> CatalogEntry | None:
    for e in CATALOG:
        if e.package == package:
            return e
    return None
