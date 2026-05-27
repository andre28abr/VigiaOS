# Vigia Rootkit Scanner

Wrapper unificado de **chkrootkit** + **Rootkit Hunter** com UI GTK4.
Parte da [Vigia Suite](../../README.md).

## O que faz

- **chkrootkit tab** — scan rapido (~30s). Procura assinaturas de
  rootkits conhecidos em binarios do sistema (substituicoes de `ps`,
  `ls`, `netstat`, modules suspeitos, interfaces promiscuas, etc.)
- **Rootkit Hunter tab** — scan completo (2-5min). 200+ checks:
  hashes de arquivos do sistema, permissoes, configs SSH/sysctl,
  processos escondidos, suspicious files
- **Historico tab** — lista de scans anteriores, com findings
  detalhados e output bruto
- **Sobre tab** — manual didatico de uso, interpretacao de resultados,
  falsos positivos comuns

## Pre-requisitos

- `chkrootkit` instalado (`rpm-ostree install chkrootkit`)
- `rkhunter` instalado (`rpm-ostree install rkhunter`)

Pode usar so um dos dois — a outra tab fica com banner "nao instalado".
Recomendado instalar ambos pra cobertura cruzada.

Use o **Vigia Tool Installer** pra instalacao 1-click.

## Como rodar

Normalmente embedded no **Vigia Hub**:
```bash
vigia-hub
# clica em "Rootkit Scanner" na sidebar (categoria Defesa & Hardening)
```

Standalone (debugging):
```bash
cd tools/rootkit-scanner
pip install --user -e .
vigia-rootkit
```

## Fluxo de uso

1. Abre a aba **chkrootkit** ou **Rootkit Hunter**
2. Clica **"Iniciar scan"**
3. Confirma + senha admin (pkexec — scanners precisam root pra checar
   `/proc`, kernel modules, `/dev/mem`)
4. Output streama em tempo real:
   - Linhas em <span style="color:#fbbf24">amarelo</span> = warnings
   - Linhas em <span style="color:#f87171">vermelho</span> = INFECTED
5. KPIs no topo atualizam ao vivo (testes, warnings, infectados)
6. Apos scan, dialog resume o resultado
7. Resultado salvo automaticamente no **Historico**

Para parar a qualquer momento, clica em **"Parar"** (aparece durante scan).

## Interpretando resultados

| Resultado | O que fazer |
|-----------|-------------|
| **Limpo** | Nenhum sinal. Repete semanalmente como rotina |
| **Warning** | Pode ser falso positivo (hashes pos-`rpm-ostree upgrade`, configs SSH, modulos NVIDIA). Revisa output |
| **Infected** | Alta probabilidade de comprometimento. Desconecta da rede, salva report, considera reinstalar |

Ver aba **Sobre** dentro do app pra guia detalhado de falsos positivos.

## LGPD / privacidade

- **100% offline** — scanners trabalham localmente, sem rede
- Reports JSON em `~/.local/share/vigia-rootkit/scans/` com **mode 0600**
  (owner-only). Diretorio com mode 0700.
- Output pode conter paths de arquivos do sistema — eh evidencia
  valida pra LGPD/audit. Recomendado arquivar 90+ dias.

## Estrutura

```
tools/rootkit-scanner/
├── pyproject.toml
├── data/
│   ├── br.com.vigia.RootkitScanner.svg
│   └── br.com.vigia.RootkitScanner.desktop
└── src/vigia_rootkit/
    ├── __init__.py / __main__.py / app.py
    ├── backend.py             # core: scanners via pkexec, parsers, reports
    ├── window.py              # 4 tabs
    └── tabs/
        ├── _helpers.py
        ├── _scan_view.py      # widget de scan reutilizavel
        ├── chkrootkit.py      # configura ScanView pra chkrootkit
        ├── rkhunter.py        # configura ScanView pra rkhunter
        ├── history.py         # lista reports salvos
        └── about.py
```

## Roadmap (v0.2+)

- Botao "Atualizar hashes" (rkhunter --propupd) na UI
- Scheduled scans via systemd timer
- Comparativo cross-scan: diff de findings entre runs
- Integration com Vigia File Integrity (AIDE) — cruza findings
- Export pra PDF via Vigia Reports
