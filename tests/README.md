# Vigia Suite — Testes (pytest)

Suite de testes para validar parsers, validators e formatters das
ferramentas da Vigia Suite. Não testa UI (GTK) — os tests assumem
backend puro.

## Setup

```bash
sudo rpm-ostree install python3-pytest
# (ou em Fedora normal: sudo dnf install python3-pytest)
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
├── common/                  # vigia_common (lib base): markdown, helpers, layout
├── hub/                     # vigia_hub: settings, status, backup, registry, tray
├── dashboard/               # vigia_dashboard: /proc parsers, alerts, format helpers
├── activity_log_gui/        # vigia_log_gui (parser/formatters da GUI)
├── dns/                     # vigia_dns (dnscrypt backend, migration, servers)
├── antivirus/               # vigia_antivirus (output parser ClamAV)
├── rootkit/                 # vigia_rootkit (parsers chkrootkit + rkhunter)
├── integrity/               # vigia_integrity (AIDE report parser)
├── hash/                    # vigia_integrity.hash_backend (algoritmos, baseline diff)
├── installer/               # vigia_installer (catálogo, extensões navegador)
├── reports/                 # vigia_reports (geração LGPD)
└── deployments/             # vigia_deployments (rpm-ostree state parser)
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
