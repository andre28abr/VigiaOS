# Vigia Reports

Gerador de relatorios **HTML** (com layout pronto pra impressao em PDF) a partir de logs do sistema. Parte do [VigiaOS](../../README.md).

## O que faz

- Coleta eventos do `journalctl` (SSH, sudo, pkexec, fail2ban) + historico do `last`/`lastb`
- Renderiza com templates Jinja2 + CSS profissional (paleta zinc + emerald)
- Salva HTML em `~/Documents/VigiaReports/`
- Abre automaticamente no navegador apos gerar — use **Imprimir → Salvar como PDF** para o PDF final
- Modo admin opcional (via `pkexec`) para coleta completa (journal do sistema, `lastb`)

## Por que HTML em vez de PDF direto

Gerar PDF via Python (WeasyPrint, ReportLab) requer dependencias pesadas (libcairo, pango) que sao complicadas em Fedora Silverblue (sistema imutavel). Usando HTML + "Imprimir como PDF" do Firefox/Chromium, a fidelidade visual e' identica e a stack fica leve.

## Templates incluidos (v0.1)

| Template | Conteudo |
|----------|----------|
| **activity_overview** | KPIs gerais + tabelas de SSH, sudo, pkexec, fail2ban, top IPs banidos |
| **auth_events** | Foco em autenticacao: SSH aceitos/falhados, sudo detalhado, pkexec, `last`, `lastb` |

## Pre-requisitos

- Python 3.11+
- Jinja2 (instalado automaticamente pelo pip)
- `journalctl`, `last` (default no Fedora)
- Para *modo admin*: `pkexec` (default no GNOME) + `lastb`

## Como rodar

```bash
cd tools/reports
pip install --user -e .
vigia-reports
```

Ou via Vigia Hub.

## Como funciona o fluxo

1. Escolhe **modelo** (combo) — descricao aparece abaixo
2. Escolhe **periodo** (24h, 7d, 30d, 90d)
3. Liga *Modo admin* se quiser dados restritos (sera pedida a senha)
4. Clica **Gerar** — progress bar pulsante enquanto coleta
5. Apos terminar, HTML abre automaticamente no navegador
6. No navegador: **Ctrl+P → Salvar como PDF** se precisar do PDF

## Estrutura

```
tools/reports/
├── pyproject.toml          # depende de jinja2
├── data/
│   ├── br.com.vigia.Reports.svg
│   └── br.com.vigia.Reports.desktop
└── src/vigia_reports/
    ├── __init__.py / __main__.py / app.py
    ├── backend.py          # coletores (journalctl, last, lastb)
    ├── renderer.py         # Jinja2 env + write_report
    ├── templates/
    │   ├── base.html       # layout + CSS embedded
    │   ├── activity_overview.html
    │   └── auth_events.html
    ├── window.py
    └── tabs/
        ├── _helpers.py
        ├── generate.py     # form + worker thread
        └── library.py      # lista de HTMLs salvos
```

## Limitacoes conhecidas

- Audit log (`audit.log`) ainda nao integrado — proxima versao
- Sem agendamento (rodar relatorios automaticamente toda semana)
- Templates fixos — proxima versao pode permitir customizacao

## Roadmap (v0.2+)

- Integracao com `vigia-log --json` (export do Activity Log) para ter o mesmo backend
- Template **lgpd_compliance** com sumario executivo para auditor externo
- Template **incident_response** com correlation de eventos
- Filtro por usuario (`--user andre`)
- Auto-relatorio semanal via systemd timer (opt-in)
- Suporte a PDF direto via WeasyPrint quando disponivel
