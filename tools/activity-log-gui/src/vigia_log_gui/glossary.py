"""Glossário do Activity Log — traduz eventos técnicos pra linguagem comum.

Puro (sem GTK), testável. Consumido pela Timeline (expander "o que é isso?"),
pelos rótulos das abas e pela aba Fontes.
"""

from __future__ import annotations

from dataclasses import dataclass

# ============================================================
# Rótulos amigáveis (PT-BR) — antes eram SUSP/INFO/OK e AUDIT/JRNL/F2B
# ============================================================

SEVERITY_LABEL = {
    "suspicious": "Atenção",
    "interesting": "Vale olhar",
    "routine": "Rotina",
}
SEVERITY_CSS = {
    "suspicious": "error",
    "interesting": "warning",
    "routine": "dim-label",
}
# Forma curta pras contagens ("3 atenção · 2 vale olhar · …")
SEVERITY_SHORT = {
    "suspicious": "atenção",
    "interesting": "vale olhar",
    "routine": "rotina",
}
SOURCE_LABEL = {
    "audit": "Auditoria de segurança",
    "journal": "Diário do sistema",
    "journald": "Diário do sistema",
    "fail2ban": "Bloqueios de IP",
    "kernel": "Kernel / boot",
    "dmesg": "Kernel / boot",
}


def severity_label(sev: str) -> str:
    return SEVERITY_LABEL.get(sev, sev)


def severity_css(sev: str) -> str:
    return SEVERITY_CSS.get(sev, "dim-label")


def severity_short(sev: str) -> str:
    return SEVERITY_SHORT.get(sev, sev)


def source_label(src: str) -> str:
    return SOURCE_LABEL.get(src, src)


# ============================================================
# Glossário "o que é isso?" — por tipo de evento
# ============================================================


@dataclass(frozen=True)
class Explanation:
    title: str    # rótulo curto ("Tentativa de login falhou")
    what: str     # o que é
    normal: str   # é normal?
    action: str   # o que fazer


# Regras (fontes_restritas, palavras-chave, Explanation). A 1ª que casar vence.
# fontes vazias = qualquer fonte. As palavras-chave casam na narrativa (já em
# pt-BR, vinda do core Rust) — incluo termos em inglês por segurança.
_RULES: list[tuple[tuple[str, ...], tuple[str, ...], Explanation]] = [
    (("fail2ban",), ("ban", "banido", "bloque"), Explanation(
        "IP bloqueado",
        "O fail2ban barrou um endereço que tentou acessar seu PC várias vezes "
        "seguidas (normalmente por SSH).",
        "É a proteção funcionando — comum em máquinas expostas à internet.",
        "Nada a fazer: o bloqueio já aconteceu. Se for um IP seu, dá pra "
        "liberar no Firewall.")),
    ((), ("falha de senha", "failed password", "authentication failure",
          "senha incorreta", "login fal", "invalid user"), Explanation(
        "Tentativa de login falhou",
        "Alguém (ou algum programa) tentou entrar e errou a senha.",
        "Normal se foi você errando a senha. Atenção se vier de fora ou em "
        "rajada.",
        "Se não foi você e há muitas tentativas, bloqueie o IP (Firewall) e "
        "confira o acesso SSH.")),
    ((), ("sudo", "pkexec", "elevou", "privilég", "como root"), Explanation(
        "Comando de administrador",
        "Um programa rodou com poderes de administrador (sudo / pkexec).",
        "Normal quando VOCÊ autoriza algo — instalar, configurar, atualizar.",
        "Se você não autorizou nada agora, vale investigar o que foi pedido.")),
    ((), ("usb", "dispositivo conectado", "new usb device", "new device"),
     Explanation(
        "Dispositivo USB conectado",
        "Um pendrive, mouse, teclado, HD ou celular foi plugado.",
        "Normal — é só você conectando algo.",
        "Estranho apenas se você não plugou nada.")),
    ((), ("memória", "memoria", "oom", "out of memory", "killed process",
          "sem memória"), Explanation(
        "Programa fechado por falta de memória",
        "A RAM acabou e o sistema fechou um programa pra não travar tudo.",
        "Acontece com pouca RAM ou um programa pesado (navegador com muitas abas).",
        "Feche programas pesados; se repetir muito, considere mais RAM.")),
    ((), ("selinux", "avc", "denied", "negou", "bloqueou o"), Explanation(
        "SELinux bloqueou uma ação",
        "O SELinux (uma proteção do sistema) impediu um programa de fazer "
        "algo fora do esperado.",
        "Às vezes é regra apertada (inofensivo), às vezes sinal de problema.",
        "Se um app legítimo parou de funcionar, o SELinux Manager ajuda a "
        "liberar com segurança.")),
    ((), ("serviço", "service", "iniciou", "started", "parou", "stopped",
          "failed", "falhou"), Explanation(
        "Serviço do sistema mudou de estado",
        "Um serviço (programa que roda em segundo plano) iniciou, parou ou "
        "falhou.",
        "Iniciar e parar é rotina. 'Falhou' merece um olhar.",
        "Se algo parou de funcionar no PC, este evento ajuda a achar o porquê.")),
    ((), ("desligou", "reiniciou", "boot", "shutdown", "reboot", "ligou"),
     Explanation(
        "Computador ligou ou desligou",
        "Registro de inicialização ou desligamento da máquina.",
        "Totalmente normal.",
        "Nada a fazer.")),
]

_SOURCE_FALLBACK = {
    "audit": Explanation(
        "Evento de auditoria",
        "Registro do subsistema de auditoria do kernel — quem fez o quê no "
        "sistema.",
        "A maioria é rotina.",
        "Use os filtros pra focar no que importa."),
    "journal": Explanation(
        "Mensagem do sistema",
        "Uma linha do diário do sistema (journald), onde os programas anotam "
        "o que fazem.",
        "Quase tudo aqui é rotina.",
        "Abra os detalhes técnicos se quiser o registro cru."),
    "fail2ban": Explanation(
        "Evento de bloqueio",
        "Mensagem do fail2ban, que bloqueia quem tenta invadir o seu PC.",
        "É proteção funcionando.",
        "Nada a fazer."),
}
_SOURCE_FALLBACK["journald"] = _SOURCE_FALLBACK["journal"]

_GENERIC = Explanation(
    "Evento do sistema",
    "Um registro de algo que aconteceu no computador.",
    "Geralmente é rotina.",
    "Abra os detalhes técnicos se quiser entender melhor.")


def explain(source: str, narrative: str, payload: dict | None = None
            ) -> Explanation:
    """Melhor explicação amigável pra um evento (casa por palavra-chave na
    narrativa; cai num texto por fonte; por fim, num genérico)."""
    low = (narrative or "").lower()
    for srcs, keys, exp in _RULES:
        if srcs and source not in srcs:
            continue
        if any(k in low for k in keys):
            return exp
    return _SOURCE_FALLBACK.get(source) or _GENERIC


# ============================================================
# Fontes (logs padrão do Fedora) — pra aba "Fontes"
# ============================================================


@dataclass(frozen=True)
class SourceInfo:
    code: str    # "journald" | "audit" | "fail2ban"
    label: str   # nome amigável
    icon: str    # icon-name do tema
    what: str    # o que é
    when: str    # quando olhar aqui


SOURCES_INFO: list[SourceInfo] = [
    SourceInfo(
        "journald", "Diário do sistema", "x-office-document-symbolic",
        "O diário central do systemd: tudo que os programas e serviços do "
        "sistema anotam enquanto rodam.",
        "Quando algo parou de funcionar, ou só pra ver o que o sistema andou "
        "fazendo."),
    SourceInfo(
        "audit", "Auditoria de segurança", "security-high-symbolic",
        "Registro de segurança do kernel: logins, uso de administrador "
        "(sudo) e acesso a arquivos sensíveis.",
        "Pra investigar acessos e ações com privilégio. Precisa do modo "
        "Admin (pkexec)."),
    SourceInfo(
        "fail2ban", "Bloqueios de IP", "network-error-symbolic",
        "O fail2ban anota cada endereço que bloqueou por tentar invadir o "
        "seu computador.",
        "Pra ver quem tentou entrar e foi barrado."),
]
