# VigiaOS — Testes (pytest)

Suite de testes para validar parsers, validators e formatters das
ferramentas do VigiaOS. Não testa UI (GTK) — os tests assumem
backend puro.

## Setup

```bash
sudo dnf install python3-pytest
```

## Rodando

```bash
cd ~/dev/VigiaOS
pytest tests/                   # tudo
pytest tests/dashboard/          # so dashboard
pytest tests/common/             # so vigia-common
pytest -v                        # verbose
pytest -k "hash"                 # match por nome
pytest --tb=long                 # tracebacks longos
```

## Markers

```bash
pytest -m "not gtk"          # pula tests que precisam GTK
pytest -m "not slow"         # pula tests lentos
pytest -m "needs_proc"       # so tests que precisam /proc (skipped no macOS)
pytest -m "integration"      # so tests com subprocess real
```

## Estrutura

```
tests/
├── conftest.py              # adiciona tools/*/src ao sys.path
├── pytest.ini               # config + markers
├── common/                  # vigia_common: markdown, layout, events (Central de Relatórios), proc, state, posture, notificações, scheduler systemd
├── hub/                     # vigia_hub: registry, adapters (Module→ToolEntry), settings, status, backup, auth/idle, tray, theme, cli, manuals, reports_html
├── products/                # registries do Red/Blue (esqueleto), Module.requires do Blue, manuais dos produtos
├── red/                     # vigia_red: recon (theHarvester), netscan (nmap), vuln (nuclei), web (wapiti), runner cancelável, handoff
├── blue/                    # vigia_blue: yara, siem, ids, memory, timeline, intel, playbooks (backends puros)
├── dashboard/               # vigia_dashboard: /proc parsers, alerts, format helpers, banda por processo, inspetor
├── activity_log_gui/        # vigia_log_gui: glossário PT-BR + fuzz
├── netmon/                  # vigia_netmon: parser de `ss` + humanização (estados PT-BR, glossário de portas)
├── dns/                     # vigia_dns: dnscrypt backend, catálogo de servers, editor TOML, migração, cancel
├── firewall/                # vigia_firewall: parser de firewall-cmd
├── selinux/                 # vigia_selinux: parsers (sestatus/semanage/ausearch)
├── hardening/               # vigia_hardening: parser Lynis + cancel
├── antivirus/               # vigia_antivirus: parser ClamAV + cancel + fuzz
├── rootkit/                 # vigia_rootkit: parsers chkrootkit + rkhunter + cancel + fuzz
├── integrity/               # vigia_integrity: parser AIDE, baseline de hash, cancel + fuzz
├── hash/                    # vigia_integrity.hash_backend: algoritmos, baseline diff
├── capabilities/            # vigia_caps: parser getcap
├── installer/               # vigia_installer: backend dnf (check-update/upgrade), catálogo de rótulos
└── reports/                 # vigia_reports: render, charts SVG, selo SHA-256, compliance, scheduler, cli, fuzz
```

## Cobertura alvo

Testar **todo o backend** sem GTK:
- Parsers (output de subprocess, /proc files)
- Validators (regex, range checks)
- Formatters (format_uptime, format_kb, format_mbps)
- Helpers genéricos (vigia_common.helpers, .markdown)
- Lógica de alertas (Dashboard alerts.py — sem Gio.Notification real)

NÃO testar:
- UI (GTK widgets, Cairo drawing)
- Integração com subprocess real (deixar como `@pytest.mark.integration`)
- pkexec (não roda em CI)

## Como adicionar testes para nova tool

1. Criar `tests/<tool>/test_<feature>.py`
2. Importar do backend: `from vigia_<tool>.backend import ...`
3. Marcar testes que precisam de `/proc` ou GTK
4. Rodar `pytest tests/<tool>/` para validar
