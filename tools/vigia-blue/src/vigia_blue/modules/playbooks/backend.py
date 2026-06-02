"""Backend do Vigia Playbooks — resposta a incidentes guiada (com trilha LGPD).

Diferente dos outros módulos do VigiaBlue, este NÃO envolve ferramenta externa:
é **conteúdo + checklist + registro**. Traz roteiros (playbooks) de resposta a
incidente prontos (contenção → erradicação → recuperação → notificação), o
usuário marca os passos cumpridos e adiciona notas, e o módulo salva um
**registro de atendimento** datado (0600) — a trilha de auditoria que a LGPD
(art. 48, comunicação à ANPD/titulares) e a boa prática de SOC exigem.

Partes PURAS (testáveis headless, sem gi):
- `playbooks()` / `get_playbook(id)` — catálogo de roteiros.
- `start_incident(pb)` / `progress(inc, pb)` / `toggle_step(inc, key)` — estado.
- `save_incident` / `list_incidents` — trilha 0600.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from vigia_common.state import load_json, save_json_0600

DATA_DIR = Path.home() / ".local" / "share" / "vigia-playbooks"
INCIDENTS_DIR = DATA_DIR


# ============================================================
# Modelo
# ============================================================


@dataclass
class Step:
    text: str
    detail: str = ""      # explicação leiga opcional


@dataclass
class Phase:
    name: str             # Contenção, Erradicação, Recuperação, Notificação…
    steps: list[Step] = field(default_factory=list)


@dataclass
class Playbook:
    id: str
    title: str
    when: str             # quando usar
    severity: str         # info | baixo | suspeito | alto | critico
    phases: list[Phase] = field(default_factory=list)


@dataclass
class Incident:
    """Um atendimento em andamento/registrado a partir de um playbook."""

    playbook_id: str
    playbook_title: str
    started_at: str
    done_steps: list[str] = field(default_factory=list)  # chaves "fase.passo"
    notes: str = ""
    closed: bool = False


# ============================================================
# Catálogo de playbooks (conteúdo pt-BR)
# ============================================================


def _pb_intrusao() -> Playbook:
    return Playbook(
        "intrusao", "Suspeita de invasão / acesso não autorizado",
        "Quando o Vigia SIEM, o Activity Log ou um sinal externo indicam que "
        "alguém pode ter entrado no sistema sem autorização.",
        "alto",
        [
            Phase("Contenção", [
                Step("Isole a máquina da rede (desconecte cabo / Wi-Fi)",
                     "Impede o invasor de continuar agindo e de se espalhar. "
                     "Não desligue ainda — preserva evidência na memória."),
                Step("Troque as senhas das contas críticas de outro dispositivo",
                     "Se a credencial vazou, a troca corta o acesso."),
                Step("Encerre sessões e conexões suspeitas",
                     "Veja o Network Monitor / `who` e finalize o que não reconhece."),
            ]),
            Phase("Investigação", [
                Step("Rode o Vigia SIEM e revise os alertas (força-bruta, sudo, conta nova)"),
                Step("Rode o Vigia YARA na pasta dos sites/uploads e em /tmp"),
                Step("Anote o que encontrou: contas, IPs, horários, arquivos"),
            ]),
            Phase("Erradicação", [
                Step("Remova contas, chaves SSH e tarefas (cron) que não reconhece"),
                Step("Reinstale o que estiver comprometido a partir de fonte confiável"),
            ]),
            Phase("Recuperação", [
                Step("Restaure dados de um backup anterior ao incidente"),
                Step("Reative a rede e monitore de perto por alguns dias"),
            ]),
            Phase("Notificação (LGPD)", [
                Step("Se houve acesso a DADOS PESSOAIS, acione o Encarregado (DPO)",
                     "Pode disparar o dever de comunicar a ANPD e os titulares (art. 48)."),
                Step("Registre tudo neste atendimento e guarde as evidências"),
            ]),
        ],
    )


def _pb_lgpd() -> Playbook:
    return Playbook(
        "lgpd_vazamento", "Vazamento de dados pessoais (LGPD)",
        "Quando dados pessoais de clientes/colaboradores podem ter sido "
        "expostos, perdidos ou acessados indevidamente.",
        "critico",
        [
            Phase("Contenção", [
                Step("Interrompa a exposição (tire o arquivo do ar, revogue acessos)"),
                Step("Preserve as evidências do como/quando aconteceu"),
            ]),
            Phase("Avaliação", [
                Step("Identifique QUAIS dados e DE QUEM foram afetados",
                     "Categorias (nome, CPF, saúde, financeiro…) e nº de titulares."),
                Step("Avalie o risco aos titulares (dano, discriminação, fraude)"),
                Step("Use o Vigia YARA / módulo LGPD p/ mapear onde há PII"),
            ]),
            Phase("Notificação (art. 48)", [
                Step("Comunique o Encarregado (DPO) imediatamente"),
                Step("Comunique a ANPD em prazo razoável",
                     "A ANPD orienta prazo de referência de 3 dias úteis. Inclua "
                     "natureza dos dados, titulares afetados, medidas tomadas."),
                Step("Comunique os titulares afetados quando houver risco relevante"),
            ]),
            Phase("Remediação", [
                Step("Corrija a causa raiz (permissão, criptografia, treinamento)"),
                Step("Documente o incidente e as medidas no registro de operações"),
            ]),
        ],
    )


def _pb_ransomware() -> Playbook:
    return Playbook(
        "ransomware", "Ransomware / arquivos criptografados",
        "Quando arquivos aparecem renomeados/criptografados e há pedido de "
        "resgate, ou o antivírus/YARA acusa ransomware.",
        "critico",
        [
            Phase("Contenção", [
                Step("Isole a máquina da rede IMEDIATAMENTE",
                     "Ransomware se espalha por compartilhamentos e rede."),
                Step("Não pague o resgate; não apague nada ainda"),
                Step("Identifique e isole outras máquinas que compartilham pastas"),
            ]),
            Phase("Investigação", [
                Step("Identifique a variante (extensão dos arquivos, nota de resgate)"),
                Step("Rode o Vigia YARA e o Antivírus para achar o executável"),
            ]),
            Phase("Recuperação", [
                Step("Restaure de backup offline limpo (anterior à infecção)"),
                Step("Reinstale o sistema se não confiar na limpeza"),
            ]),
            Phase("Notificação (LGPD)", [
                Step("Se dados pessoais foram afetados, siga o playbook de LGPD"),
            ]),
        ],
    )


def _pb_conta() -> Playbook:
    return Playbook(
        "conta_comprometida", "Conta comprometida (senha/credencial)",
        "Quando uma senha vazou, houve login estranho ou o SIEM acusou "
        "força-bruta bem-sucedida.",
        "alto",
        [
            Phase("Contenção", [
                Step("Troque a senha da conta afetada agora"),
                Step("Encerre todas as sessões ativas dessa conta"),
                Step("Ative verificação em duas etapas (2FA) onde possível"),
            ]),
            Phase("Investigação", [
                Step("Veja o que a conta acessou enquanto comprometida (Activity Log)"),
                Step("Verifique se a mesma senha era usada em outros serviços"),
            ]),
            Phase("Recuperação", [
                Step("Revogue tokens/chaves criados pela conta no período"),
                Step("Monitore a conta por atividade anormal nos próximos dias"),
            ]),
        ],
    )


def _pb_malware() -> Playbook:
    return Playbook(
        "malware", "Malware detectado",
        "Quando o Antivírus, o Rootkit Scanner ou o Vigia YARA acusam um "
        "arquivo malicioso.",
        "suspeito",
        [
            Phase("Contenção", [
                Step("Não execute o arquivo; coloque em quarentena"),
                Step("Desconecte da rede se suspeitar de atividade ativa"),
            ]),
            Phase("Investigação", [
                Step("Confirme com um segundo scanner (YARA + Antivírus)"),
                Step("Descubra a origem (download, e-mail, pendrive)"),
            ]),
            Phase("Erradicação", [
                Step("Remova o arquivo e artefatos relacionados"),
                Step("Verifique persistência (cron, serviços, autostart)"),
            ]),
        ],
    )


_PLAYBOOKS = [_pb_intrusao(), _pb_lgpd(), _pb_ransomware(), _pb_conta(), _pb_malware()]


def playbooks() -> list[Playbook]:
    return list(_PLAYBOOKS)


def get_playbook(pid: str) -> Playbook | None:
    for pb in _PLAYBOOKS:
        if pb.id == pid:
            return pb
    return None


# ============================================================
# Estado de um atendimento (puro)
# ============================================================


def step_key(phase_idx: int, step_idx: int) -> str:
    return f"{phase_idx}.{step_idx}"


def total_steps(pb: Playbook) -> int:
    return sum(len(ph.steps) for ph in pb.phases)


def start_incident(pb: Playbook) -> Incident:
    return Incident(
        playbook_id=pb.id, playbook_title=pb.title,
        started_at=datetime.now().isoformat(timespec="seconds"),
    )


def toggle_step(inc: Incident, key: str) -> None:
    if key in inc.done_steps:
        inc.done_steps.remove(key)
    else:
        inc.done_steps.append(key)


def progress(inc: Incident, pb: Playbook) -> tuple[int, int]:
    """(passos cumpridos, total). Conta só chaves válidas do playbook."""
    valid = {step_key(pi, si)
             for pi, ph in enumerate(pb.phases)
             for si in range(len(ph.steps))}
    done = len([k for k in inc.done_steps if k in valid])
    return done, len(valid)


# ============================================================
# Trilha de atendimentos (0600)
# ============================================================


def _ensure_dir() -> Path:
    INCIDENTS_DIR.mkdir(parents=True, exist_ok=True)
    return INCIDENTS_DIR


def save_incident(inc: Incident) -> Path | None:
    """Salva o atendimento em ~/.local/share/vigia-playbooks/incident-<ts>.json (0600)."""
    if not inc.started_at:
        return None
    rd = _ensure_dir()
    safe_ts = inc.started_at.replace(":", "-").replace(".", "_")
    path = rd / f"incident-{safe_ts}.json"
    data = {
        "playbook_id": inc.playbook_id,
        "playbook_title": inc.playbook_title,
        "started_at": inc.started_at,
        "done_steps": inc.done_steps,
        "notes": inc.notes,
        "closed": inc.closed,
    }
    return path if save_json_0600(path, data) else None


def list_incidents(limit: int = 50) -> list[dict]:
    """Atendimentos salvos, mais novos primeiro (descarta corrompidos)."""
    if not INCIDENTS_DIR.is_dir():
        return []
    files = sorted(
        INCIDENTS_DIR.glob("incident-*.json"),
        key=lambda p: p.stat().st_mtime, reverse=True,
    )
    out: list[dict] = []
    for f in files[:limit]:
        data = load_json(f)
        if isinstance(data, dict):
            data["_file"] = str(f)
            out.append(data)
    return out
