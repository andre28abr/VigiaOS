# Vigia Dashboard

Dashboard de sistema em tempo real para Linux desktop. CPU, memória,
disco, rede e processos com gráficos via Cairo + GTK4.

Substitui o uso de `htop`, `btop`, `glances`, `iotop` e `iftop` —
visualização nativa em UI moderna, sem terminal.

## Status

v0.1.0 — alpha. Funcional para todas as métricas principais.

## Features

- **Visão Geral** com KPIs: uptime, load avg, sparklines de CPU/RAM/rede
- **Gráficos detalhados** com Cairo: CPU por core, memória + swap, I/O por
  disco, bandwidth por interface
- **Top processos** com filtros, ordenação e kill (com confirmação)
- **Multi-cor semântico**: CPU=emerald, RAM=amber, Disco=ciano, Rede=violeta
- **Refresh 1Hz** (configurável internamente)
- **Histórico** dos últimos 60s em memória (sem persistência)
- **Sem dependências externas pip** — usa só Python stdlib + PyGObject
- **Sem subprocess para a maioria das métricas** — leitura direta de `/proc`

## Setup

```bash
# Nenhum pacote externo necessário — usa /proc
# Opcional para temperaturas:
sudo dnf install lm_sensors
sudo sensors-detect --auto

pip install --user -e .
vigia-dashboard
```

## Wrapper de

- `procfs` (kernel interface — sem pacote)
- `lm_sensors` (opcional, para temperatura)

## Roadmap

- v0.2: alertas configuráveis (load > 4, mem > 90%, disk > 95%)
- v0.2: integração com Activity Log (logs filtrados por contexto)
- v0.3: histórico persistente (últimos 7 dias) em SQLite
- v0.3: exportar snapshot pro PDF (Reports)
