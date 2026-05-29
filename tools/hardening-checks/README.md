# Vigia Hardening Checks

Wrapper GTK4 do **Lynis** com UI focada em Hardening Index, warnings e suggestions.

Parte do [VigiaOS](../../README.md).

## O que faz

- Roda `lynis audit system` (~250 controles de seguranca) via `pkexec`
- Parseia `/var/log/lynis-report.dat` automaticamente
- Mostra **Hardening Index** (0–100) em destaque com avaliacao qualitativa
- Lista warnings (criticas) e suggestions (melhorias) com busca + filtro por categoria
- Visao por **categoria** (AUTH, BOOT, KRNL, MACF, NETW, etc.) com labels pt-BR

## Por que existe

Lynis e' a ferramenta mais popular de auditoria de hardening no Linux, mas o output e' um wall-of-text em terminal. Esta tool transforma isso numa interface escaneavel — util para escritorio de advocacia que precisa demonstrar postura de seguranca para LGPD.

## Pre-requisitos

- Fedora Silverblue (ou similar) com Lynis instalado:
  ```bash
  rpm-ostree install lynis
  systemctl reboot
  ```
- `polkit` (instalado por padrao no GNOME)

## Como rodar

Em desenvolvimento (editavel):
```bash
cd tools/hardening-checks
pip install --user -e .
vigia-hardening
```

Ou via Vigia Hub (botao "Abrir").

## Estrutura

```
tools/hardening-checks/
├── pyproject.toml
├── data/
│   ├── br.com.vigia.HardeningChecks.svg
│   └── br.com.vigia.HardeningChecks.desktop
└── src/vigia_hardening/
    ├── __init__.py / __main__.py / app.py
    ├── backend.py         # parser de lynis-report.dat + run_audit_blocking
    ├── window.py          # Adw.ViewStack com 4 tabs
    └── tabs/
        ├── _helpers.py    # make_clamp, severity_*, show_error
        ├── overview.py    # Hardening Index hero + botao Auditar
        ├── warnings.py    # FindingsListTab base + WarningsTab
        ├── suggestions.py # SuggestionsTab (herda de FindingsListTab)
        └── categories.py  # grouping por test category
```

## Categorias suportadas

A backend traduz codigos do Lynis para nomes pt-BR (ver `CATEGORY_LABELS` em
`backend.py`). Exemplos:

| Codigo | Categoria |
|--------|-----------|
| AUTH   | Autenticacao |
| BOOT   | Boot e loader |
| FIRE   | Firewall |
| KRNL   | Kernel e sysctl |
| MACF   | MAC (SELinux/AppArmor) |
| NETW   | Rede |
| SSH    | Servidor SSH |
| STRG   | Storage / discos |

## Limitacoes conhecidas

- Audit completo pode levar 2-5 minutos. UI mostra progress indeterminada.
- O parser e' tolerante mas se o formato do `lynis-report.dat` mudar drasticamente em versoes futuras pode quebrar.
- Hardening Index e' uma metrica do Lynis — nao e' uma certificacao formal.

## Roadmap (v0.2+)

- Filtro temporal (auditorias anteriores em arquivo)
- Export PDF/HTML (integrar com Vigia Reports quando existir)
- Action items: clicar num finding e ver sugestao de remediation
- Auto-audit semanal via systemd timer (opcional)
