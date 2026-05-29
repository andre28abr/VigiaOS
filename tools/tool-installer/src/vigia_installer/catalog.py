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
    # NOTA: nmap e tcpdump removidos do catalogo (2026-05-29). Sao
    # ferramentas de recon/sniffing de perfil ofensivo — vao pro projeto
    # **Vigia Red** (pentest). nmap era inclusive o backend da GUI Network
    # Scanner, ja removida ("risco etico, Lei 12.737"). O foco do Vigia Hub
    # aqui e defesa/auditoria/privacidade, nao recon ativo de rede.
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
    # NOTA: htop e iotop removidos do catalogo (2026-05-30). O **Vigia
    # Dashboard** (ja incluso na suite) cobre os dois em GUI nativa: a aba
    # Processos ordena por CPU/mem e por I/O (read+write) por processo
    # (le /proc/<pid>/io, v0.2) e tem kill — exatamente htop + iotop.
    # Listar os CLIs aqui era redundante. lsof/strace ficam (nicho de
    # debug que nenhuma GUI da suite cobre); fail2ban e' servico de defesa.
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
            "arquivo `.conf` curto. No GNOME, o **NetworkManager** ja "
            "importa e gerencia tuneis WireGuard nativamente "
            "(Configuracoes -> Rede -> VPN), sem precisar de tool dedicada."
        ),
        category="privacidade",
        binary="wg",
    ),
    CatalogEntry(
        package="dnscrypt-proxy",
        name="dnscrypt-proxy",
        description="DNS over HTTPS/TLS local (backend do Vigia DNS Manager).",
        why=(
            "**Encripta as queries DNS** que normalmente vao em texto puro. "
            "Roda como servico local que substitui o resolver default, com "
            "suporte a **DoH/DoT** e servidores sem log.\n\n"
            "*E' o backend do **Vigia DNS Manager** — instale por aqui e "
            "gerencie tudo na tool (escolha do resolver, aplicar, status), "
            "sem editar `/etc/dnscrypt-proxy/dnscrypt-proxy.toml` na mao.*"
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
    # NOTA: ClamTK removido do catalogo. O Vigia tem GUI propria para o
    # ClamAV (Vigia Antivirus — usa clamav como backend). O clamav (pacote)
    # continua no catalogo pra que a tool Vigia possa usar.
    # NOTA: binwalk removido do catalogo (2026-05-29). RE de firmware/
    # binarios e' nicho ofensivo/CTF — vai pro **Vigia Red**. Era o backend
    # da GUI Firmware Analyzer, ja removida pelo mesmo motivo.
    CatalogEntry(
        # NOTA: o binario chama-se `hashdeep`, mas o PACOTE no Fedora e'
        # `md5deep` (a suite md5deep/sha256deep/hashdeep). `rpm-ostree
        # install hashdeep` falha com "Packages not found" (2026-05-30).
        package="md5deep",
        name="hashdeep",
        description="Computa hashes recursivamente + compara conjuntos.",
        why=(
            "Quando voce quer hashear uma pasta inteira e depois verificar se "
            "**algum arquivo mudou** sem precisar de baseline AIDE. Util para "
            "cadeia de custodia em casos forenses.\n\n"
            "*No Fedora vem no pacote **`md5deep`** (inclui `hashdeep`, "
            "`md5deep`, `sha256deep`). O **Vigia File Integrity** usa o "
            "`hashdeep` como motor opcional na aba Baseline.*"
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
