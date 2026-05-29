# Vigia Activity Log GUI

Frontend **GTK4** do `vigia-log` (parser Rust). Parte do [VigiaOS](../../README.md).

## Arquitetura

```
+---------------------+         +-------------------+
|  vigia-log-gui      |         |  vigia-log        |
|  (Python + GTK4)    | ──────► |  (Rust + Ratatui) |
|                     |   exec  |                   |
|  - UI               |         |  - parser audit   |
|  - filtros          | ◄────── |  - parser journal |
|  - search           |  json   |  - parser f2b     |
|  - render           |         |  - narrator       |
+---------------------+         |  - correlator     |
                                |  - classifier     |
                                +-------------------+
```

A GUI Python **nao reimplementa** parsing — chama `vigia-log --output json-bundle`
e renderiza o resultado. Toda a logica de classificacao (routine/interesting/suspicious)
e correlation (fail2ban_burst, oom_kill, etc.) continua no Rust onde performance
importa.

Vantagens:
- Performance Rust mantida (audit.log com 100k+ linhas continua rapido)
- UI consistente com a suite (GTK4 + libadwaita, paleta zinc + emerald)
- Embedable no Hub single-window mode
- Cross-tool integration trivial (Reports pode chamar o mesmo bundle)

## Pre-requisitos

- `vigia-log` instalado no PATH (binary Rust)
- Python 3.11+
- Para audit/journal completo: `pkexec` (Modo admin)

## Como rodar

```bash
cd tools/activity-log-gui
pip install --user -e .
vigia-log-gui
```

Ou via Vigia Hub.

## Fluxo

1. Header tem switch **Admin** + botao **Atualizar**
2. Sem Admin: roda `vigia-log` direto (so journald user-level)
3. Com Admin: roda `pkexec vigia-log` (audit + journal sistema + fail2ban) — 1 senha
4. Bundle JSON chega, renderiza nas 3 tabs:
   - **Status**: hero card + KPIs + sources disponiveis
   - **Timeline**: ListBox dos eventos com filtros (severidade, source) + search + expand pra ver payload raw
   - **Correlations**: padroes cross-source com badges de severidade

## Schema do JSON bundle

```json
{
  "version": 1,
  "generated_at": "2026-05-23 17:45:00",
  "sources": ["audit", "journald", "fail2ban"],
  "events_count": 234,
  "correlations_count": 3,
  "events": [
    {
      "timestamp": "2026-05-23 14:32:01",
      "source": "audit",
      "severity": "suspicious",
      "narrative": "14:32:01 — autenticacao via /usr/bin/ssh: usuario `root` FALHOU",
      "payload": { "audit_id": 1234, "records": [...] }
    }
  ],
  "correlations": [
    {
      "kind": "fail2ban_burst",
      "severity": "interesting",
      "timestamp": "...",
      "end": "...",
      "summary": "fail2ban baniu 192.0.2.42 apos 3 tentativas SSH em 10s",
      "contributing_count": 4
    }
  ]
}
```

## Estrutura

```
tools/activity-log-gui/
├── pyproject.toml
├── data/
│   ├── br.com.vigia.ActivityLog.svg
│   └── br.com.vigia.ActivityLog.desktop
└── src/vigia_log_gui/
    ├── __init__.py / __main__.py / app.py
    ├── backend.py         # invoca vigia-log + parseia bundle
    ├── window.py          # header (Admin + Atualizar) + 3 tabs
    └── tabs/
        ├── _helpers.py    # severity_css, source_label, etc.
        ├── status.py      # hero + KPIs + sources
        ├── timeline.py    # ListBox filtravel + expand row mostra payload
        └── correlations.py
```

## Roadmap (v0.2+)

- **Live mode** — refresh automatico a cada N segundos (precisa lidar com polkit cache)
- Filtro por **tipo de audit** (USER_AUTH, AVC, USER_CMD, etc.)
- Filtro por **periodo** (last hour, last 24h, custom)
- **Export pra Reports** — botao gera HTML a partir do bundle atual
- **Notificacao desktop** quando suspicious aparecer (com live mode)
- **Mini-grafico** de eventos/hora no Status
