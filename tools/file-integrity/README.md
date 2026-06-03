# Vigia File Integrity

Wrapper GTK4 do **AIDE** (Advanced Intrusion Detection Environment). Parte do [VigiaOS](../../README.md).

## O que faz

- **Baseline**: snapshot inicial dos arquivos do sistema (hashes SHA256, permissoes, mtime, size, owner)
- **Verificar**: compara estado atual com baseline e reporta diferencas
- **Re-baseline**: aceita as mudancas atuais como nova referencia (apos updates legitimos)
- Tudo numa **unica chamada `pkexec`** por operacao (sem repetir senha)

## Por que existe

AIDE e' a ferramenta classica de file integrity monitoring (FIM) no Linux, mas o uso e' via CLI com config em `/etc/aide.conf` e comandos pouco amigaveis. Esta tool da:

- Visao clara do estado: <em>integro</em> / <em>mudancas detectadas</em> / <em>sem baseline</em>
- Lista de mudancas com badges coloridos (verde=adicionado, vermelho=removido, ambar=modificado)
- Re-baseline com confirmacao explicita (evita aceitar mudancas suspeitas por engano)

Util para **escritorio de advocacia** demonstrar postura LGPD (controle de integridade de sistemas que tratam dados pessoais).

## Pre-requisitos

```bash
sudo dnf install aide
```

## Como rodar

```bash
cd tools/file-integrity
pip install --user -e .
vigia-integrity
```

Ou via Vigia Hub.

## Fluxo tipico

1. **Primeira vez**: aba `Status` → botao `Criar baseline` (demora 5-30 min dependendo do sistema)
2. **Periodicamente**: botao `Verificar` (3-10 min). Se zerou → tudo integro. Se mudou → ver aba `Mudancas`.
3. **Apos `sudo dnf upgrade`**: as mudancas serao esperadas → botao `Re-baseline` aceita
4. **Mudancas inesperadas**: NAO clique re-baseline. Investigue antes (compare com Activity Log, veja sudo invocations no Reports).

## Estrutura

```
tools/file-integrity/
├── pyproject.toml
├── data/
│   ├── br.com.vigia.FileIntegrity.svg
│   └── br.com.vigia.FileIntegrity.desktop
└── src/vigia_integrity/
    ├── __init__.py / __main__.py / app.py
    ├── backend.py             # aide --init/check/update + parse output
    ├── window.py              # 3 tabs (Status + Mudancas + Sobre)
    └── tabs/
        ├── _helpers.py
        ├── status.py          # hero card + stats + acoes
        ├── changes.py         # lista filtravel de mudancas
        └── about.py           # explicacao do AIDE + watched paths
```

## Estado persistido

Resumo do ultimo check fica em `~/.config/vigia/file-integrity.json` para a UI mostrar mesmo apos restart:

```json
{
  "last_check": {
    "timestamp": "2026-05-23T17:00:00",
    "total_entries": 102943,
    "added": 3, "removed": 1, "changed": 7,
    "duration_seconds": 412
  }
}
```

A *lista detalhada* de mudancas e' guardada apenas em memoria (re-roda `Verificar` para popular).

## Roadmap (v0.2+)

- View detalhada de cada mudanca (hash velho vs novo, mtime velho vs novo)
- Diff de conteudo para arquivos texto pequenos
- Systemd timer opcional (`vigia-integrity-check.timer` semanal)
- Notificacao desktop quando ha mudancas
- Export de resultado para Vigia Reports (template "integrity_audit")
- Editor visual de `/etc/aide.conf` com presets (mais paths / menos paths)
- Detecao de "esqueci de re-baselinear apos update" via comparacao de mtime do baseline com `/etc/os-release`

## Notas

- AIDE pode demorar bastante em sistemas com muitos arquivos. Os limites de timeout (30min) sao defensivos — auditorias normais ficam em 5-15 min.
- O baseline cresce com o sistema (geralmente ~50-200 MB comprimido).
- `aide --check` consome bastante I/O — evite rodar simultaneamente a updates pesados.
