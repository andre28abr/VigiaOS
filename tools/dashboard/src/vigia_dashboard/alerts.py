"""Sistema de alertas configuraveis (v0.2).

Modelo:
- AlertRule: configuracao persistida (metric, threshold, duration, cooldown)
- AlertState: tracking em memoria (quanto tempo esta acima do threshold)
- AlertEvent: alerta efetivamente disparado

Persistencia: ~/.config/vigia/dashboard-alerts.json com mode 0600.

Metrics suportadas (todas em valores numericos comparaveis com threshold):
- cpu_pct: 0-100
- mem_pct: 0-100
- swap_pct: 0-100
- disk_pct_<mount>: 0-100 (por mountpoint — ex: 'disk_pct_/')
- load_1: load average 1min (raw)
- cpu_temp_c: temperatura CPU em Celsius

Operador: 'gt' (>) e 'lt' (<).
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path


CONFIG_DIR = Path.home() / ".config" / "vigia"
CONFIG_PATH = CONFIG_DIR / "dashboard-alerts.json"


# ============================================================
# Metricas disponiveis (para UI exibir e validar)
# ============================================================


METRICS: dict[str, dict] = {
    "cpu_pct": {
        "label": "Uso de CPU (%)",
        "unit": "%",
        "default_threshold": 95.0,
        "default_op": "gt",
        "range": (0, 100),
    },
    "mem_pct": {
        "label": "Uso de RAM (%)",
        "unit": "%",
        "default_threshold": 90.0,
        "default_op": "gt",
        "range": (0, 100),
    },
    "swap_pct": {
        "label": "Uso de Swap (%)",
        "unit": "%",
        "default_threshold": 50.0,
        "default_op": "gt",
        "range": (0, 100),
    },
    "load_1": {
        "label": "Load average 1min",
        "unit": "",
        "default_threshold": 4.0,
        "default_op": "gt",
        "range": (0, 100),
    },
    "cpu_temp_c": {
        "label": "Temperatura CPU (°C)",
        "unit": "°C",
        "default_threshold": 85.0,
        "default_op": "gt",
        "range": (0, 150),
    },
    "disk_pct_root": {
        "label": "Uso de disco em /",  # path "/" intencional, sem diacritico
        "unit": "%",
        "default_threshold": 90.0,
        "default_op": "gt",
        "range": (0, 100),
    },
    "disk_pct_home": {
        "label": "Uso de disco em /home",
        "unit": "%",
        "default_threshold": 90.0,
        "default_op": "gt",
        "range": (0, 100),
    },
}


def metric_label(metric_id: str) -> str:
    """Helper para UI mostrar nome humano da metrica."""
    meta = METRICS.get(metric_id)
    return meta["label"] if meta else metric_id


# ============================================================
# Dataclasses
# ============================================================


@dataclass
class AlertRule:
    """Configuracao de um alerta — persistido em JSON."""
    id: str                           # uuid hex
    metric: str                       # chave de METRICS
    threshold: float
    op: str = "gt"                    # 'gt' ou 'lt'
    duration_sec: int = 30            # tempo minimo acima do threshold
    cooldown_sec: int = 300           # min entre alertas do mesmo rule
    label: str = ""                   # nome amigavel (default: gerado)
    enabled: bool = True


@dataclass
class AlertState:
    """Tracking de uma regra em memoria — quanto tempo esta tripping."""
    rule_id: str
    above_since: float = 0.0          # epoch quando comecou a violar
    last_fired_at: float = 0.0        # epoch ultima vez que disparou


@dataclass
class AlertEvent:
    """Alerta disparado — payload para notificacao."""
    rule_id: str
    rule_label: str
    metric: str
    metric_label: str
    threshold: float
    current_value: float
    op: str
    fired_at: float


# ============================================================
# Config IO
# ============================================================


def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(CONFIG_DIR, 0o700)
    except OSError:
        pass


def load_rules() -> list[AlertRule]:
    """Carrega regras de alertas do JSON. Se nao existir, retorna defaults."""
    if not CONFIG_PATH.exists():
        return _default_rules()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return _default_rules()
    # HARDENING: config editavel/corrompivel — valida shape antes de iterar.
    raw_rules = data.get("rules", []) if isinstance(data, dict) else []
    if not isinstance(raw_rules, list):
        raw_rules = []
    rules = []
    for r in raw_rules:
        if not isinstance(r, dict):
            continue
        try:
            rules.append(AlertRule(
                id=r["id"],
                metric=r["metric"],
                threshold=float(r["threshold"]),
                op=r.get("op", "gt"),
                duration_sec=int(r.get("duration_sec", 30)),
                cooldown_sec=int(r.get("cooldown_sec", 300)),
                label=r.get("label", ""),
                enabled=bool(r.get("enabled", True)),
            ))
        except (KeyError, ValueError, TypeError):
            continue
    return rules if rules else _default_rules()


def save_rules(rules: list[AlertRule]) -> tuple[bool, str]:
    """Salva regras no JSON com chmod 0600."""
    _ensure_config_dir()
    data = {"rules": [asdict(r) for r in rules]}
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.chmod(CONFIG_PATH, 0o600)
        return True, ""
    except OSError as e:
        return False, f"Falha ao salvar: {e}"


def _default_rules() -> list[AlertRule]:
    """Regras default razoaveis para primeira instalacao."""
    import uuid
    return [
        AlertRule(
            id=uuid.uuid4().hex,
            metric="cpu_pct",
            threshold=95.0,
            op="gt",
            duration_sec=60,
            cooldown_sec=600,
            label="CPU alta sustentada",
            enabled=False,  # opt-in
        ),
        AlertRule(
            id=uuid.uuid4().hex,
            metric="mem_pct",
            threshold=90.0,
            op="gt",
            duration_sec=30,
            cooldown_sec=600,
            label="Memória quase cheia",
            enabled=False,
        ),
        AlertRule(
            id=uuid.uuid4().hex,
            metric="cpu_temp_c",
            threshold=85.0,
            op="gt",
            duration_sec=15,
            cooldown_sec=300,
            label="Temperatura CPU crítica",
            enabled=False,
        ),
        AlertRule(
            id=uuid.uuid4().hex,
            metric="disk_pct_root",
            threshold=95.0,
            op="gt",
            duration_sec=5,
            cooldown_sec=3600,
            label="Disco / quase cheio",
            enabled=False,
        ),
    ]


def new_rule_id() -> str:
    """Gera novo UUID para nova rule."""
    import uuid
    return uuid.uuid4().hex


# ============================================================
# AlertManager
# ============================================================


class AlertManager:
    """Mantem estado das regras e dispara AlertEvents.

    Uso:
        mgr = AlertManager()
        mgr.set_rules(rules)
        events = mgr.check(metrics_snapshot)  # chamado a cada tick
        for e in events:
            # disparar notificacao
    """

    def __init__(self) -> None:
        self._rules: list[AlertRule] = []
        self._states: dict[str, AlertState] = {}

    def set_rules(self, rules: list[AlertRule]) -> None:
        """Substitui regras. State de regras removidas e' descartado."""
        self._rules = rules
        # Limpa state de regras nao mais presentes
        active_ids = {r.id for r in rules}
        self._states = {k: v for k, v in self._states.items() if k in active_ids}

    def get_rules(self) -> list[AlertRule]:
        return list(self._rules)

    def check(self, metrics: dict[str, float]) -> list[AlertEvent]:
        """Avalia todas as regras contra snapshot atual de metricas.

        Args:
            metrics: dict {metric_id: current_value}.

        Retorna lista de AlertEvents para disparar (respeitando duration
        e cooldown).
        """
        events: list[AlertEvent] = []
        now = time.time()

        for rule in self._rules:
            if not rule.enabled:
                # Reseta state se desabilitada
                self._states.pop(rule.id, None)
                continue

            current = metrics.get(rule.metric)
            if current is None:
                continue

            # Verifica se viola
            violates = (
                (rule.op == "gt" and current > rule.threshold) or
                (rule.op == "lt" and current < rule.threshold)
            )

            state = self._states.get(rule.id)
            if state is None:
                state = AlertState(rule_id=rule.id)
                self._states[rule.id] = state

            if not violates:
                # Saiu do estado de violacao — reseta clock
                state.above_since = 0.0
                continue

            # Esta violando
            if state.above_since == 0.0:
                state.above_since = now

            # Tempo total de violacao
            duration = now - state.above_since

            # Cooldown desde ultimo fire
            cooldown_elapsed = now - state.last_fired_at

            # Dispara se acima do threshold por tempo suficiente E fora do cooldown
            if duration >= rule.duration_sec and cooldown_elapsed >= rule.cooldown_sec:
                events.append(AlertEvent(
                    rule_id=rule.id,
                    rule_label=rule.label or metric_label(rule.metric),
                    metric=rule.metric,
                    metric_label=metric_label(rule.metric),
                    threshold=rule.threshold,
                    current_value=current,
                    op=rule.op,
                    fired_at=now,
                ))
                state.last_fired_at = now

        return events
