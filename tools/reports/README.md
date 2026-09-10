# Vigia Reports

Gerador de relatorios **HTML** (com layout pronto pra impressao em PDF) a partir de logs do sistema. Parte do [VigiaOS](../../README.md).

## O que faz

- Coleta eventos do `journalctl` (SSH, sudo, pkexec, fail2ban) + historico do `last`/`lastb`
- Renderiza com templates Jinja2 + CSS profissional (paleta zinc + emerald)
- Salva HTML em `~/.local/share/vigia-reports/` (arquivos `0600`, fora de pastas sincronizadas com nuvem — relatórios têm PII). `~/Documents/VigiaReports/` é só um caminho legado, migrado automaticamente uma vez
- Abre automaticamente no navegador apos gerar — use **Imprimir → Salvar como PDF** para o PDF final
- Modo admin opcional (via `pkexec`) para coleta completa (journal do sistema, `lastb`)

## Por que HTML em vez de PDF direto

Gerar PDF via Python (WeasyPrint, ReportLab) requer dependencias pesadas (libcairo, pango) que aumentam a superficie de instalacao. Usando HTML + "Imprimir como PDF" do Firefox/Chromium, a fidelidade visual e' identica e a stack fica leve.

## Templates incluidos (6 + base)

| Template | Conteudo |
|----------|----------|
| **activity_overview** | KPIs gerais + tabelas de SSH, sudo, pkexec, fail2ban, top IPs banidos |
| **auth_events** | Foco em autenticacao: SSH aceitos/falhados, sudo detalhado, pkexec, `last`, `lastb` |
| **admin_access** | Quem usou privilegio de administrador (sudo/pkexec) e quando |
| **executive_summary** | Sumario executivo curto, pra quem nao e' tecnico |
| **lgpd_compliance** | Evidencias de diligencia (LGPD) pra auditor externo |
| **system_health** | Saude do sistema (updates, servicos, disco) |

Todo relatorio sai com **selo SHA-256** e a **identidade do escritorio** (nome/logo configuraveis); ha **agendamento mensal** headless (timer do usuario).

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

Ou via VigiaOS (seção Hub).

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
    │   ├── activity_overview.html / auth_events.html
    │   ├── admin_access.html / executive_summary.html
    │   └── lgpd_compliance.html / system_health.html
    ├── window.py
    └── tabs/
        ├── _helpers.py
        ├── generate.py     # form + worker thread
        └── library.py      # lista de HTMLs salvos
```

## Limitacoes conhecidas

- Templates fixos — customizacao alem da identidade do escritorio fica pra depois
- PDF direto (WeasyPrint) continua **fora** de proposito: HTML + "Imprimir como PDF" mantem a stack leve

Roadmap geral em [DEVELOPMENT.md §10](../../DEVELOPMENT.md#10-roadmap).
