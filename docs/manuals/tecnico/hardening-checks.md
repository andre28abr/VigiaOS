# Hardening Checks (hardening-checks)

## Em uma frase

Wrapper GTK4 do **Lynis** — roda `lynis audit system` via pkexec e
apresenta o Hardening Index + warnings + suggestions numa interface
escaneável em vez do wall-of-text do terminal.

## O que envolve

| Item | Valor |
|---|---|
| **Pacotes Linux** | `lynis` |
| **Comando principal** | `pkexec bash -c "lynis audit system --quiet --no-colors; chmod 640 /var/log/lynis-report.dat"` |
| **Permissões** | Lynis lê `/etc/shadow`, sysctl, etc — precisa root via Polkit |
| **Stack** | Python 3.11+ · PyGObject · GTK4 · libadwaita 1 |
| **Path config** | Sem state local — lê `/var/log/lynis-report.dat` (formato chave=valor) |
| **App ID** | `br.com.vigia.HardeningChecks` |
| **Versão** | 0.1.2 |

## Arquitetura interna

```
vigia_hardening/
├── backend.py     — parser de /var/log/lynis-report.dat + run_audit_blocking()
├── window.py      — _HardeningContent controller + build_content()
└── tabs/
    ├── overview.py    — Hardening Index hero + stats + botão "Executar"
    ├── warnings.py    — FindingsListTab base + warnings
    ├── suggestions.py — subclasse override que mostra suggestions
    └── categories.py  — findings agrupados por prefixo (KRNL, AUTH, BOOT, MACF...)
```

Padrão controller: `_HardeningContent` mantém o `LynisReport` corrente
e chama `tab.refresh(report)` em todas as tabs sempre que parseia o
arquivo de novo. Audit finaliza → callback `_reload_and_refresh` →
`parse_report()` → broadcast para as 4 tabs.

`run_audit_blocking()` é chamada em `threading.Thread(daemon=True)` (UI
mostra ProgressBar pulsante via `GLib.timeout_add(100, pulse)`). Timeout
de 600s — Lynis típico leva 2-5 min.

## Comandos disparados

```bash
# Audit completo (precisa root)
pkexec bash -c '
set +e
lynis audit system --quiet --no-colors
rc=$?
# Permissão 640 + chown grupo para o user (LGPD: não world-readable)
if [ -n "$VIGIA_TARGET_USER" ]; then
    chown root:"$VIGIA_TARGET_USER" /var/log/lynis-report.dat 2>/dev/null || true
    chown root:"$VIGIA_TARGET_USER" /var/log/lynis.log 2>/dev/null || true
fi
chmod 640 /var/log/lynis-report.dat 2>/dev/null || true
chmod 640 /var/log/lynis.log 2>/dev/null || true
exit $rc
'

# Output bruto disponível depois em:
ls -l /var/log/lynis-report.dat  # formato key=value
ls -l /var/log/lynis.log
```

### Por que o chmod 640 + chown?

Bug fix crítico: Lynis roda como root via pkexec e grava
`/var/log/lynis-report.dat` com perms 600 (root only). Sem o chmod, o
backend rodando como user não consegue ler o report — parser
silenciosamente retorna vazio (UI mostra "Não avaliado").

LGPD hardening: 640 + grupo = apenas root e o user que iniciou a
auditoria leem. 644 deixaria world-readable (vazaria info de
configuração de host para qualquer user logado).

Segurança contra injection: `$USER` validado por regex POSIX
(`^[a-z_][a-z0-9_-]{0,31}\$?$`) antes de virar `VIGIA_TARGET_USER` no
env do subprocess. Atacante setando `USER='root && rm -rf /'` antes de
abrir a GUI não consegue injetar — script bash referencia
`"$VIGIA_TARGET_USER"` como variável (quoted).

## Tabs / Funcionalidades

### Resumo (Overview)

- **Hero box**: Hardening Index gigante (0-100) + label de severidade
  + ProgressBar
- **Stats group**: warnings count, suggestions count, tests executed,
  tests skipped (com explicação: o Lynis pula testes que não se aplicam
  ao sistema), última execução (`ha X min/horas/dias`)
- **Context banner**: aparece condicionalmente:
  - Rodou mas não gerou hardening_index → erro
  - Sem findings → talvez bem configurado OU parser falhou
  - >30% de tests skipped → normal (serviços/recursos não instalados), explica
- **Action group**: botão "Executar auditoria completa" (ProgressBar
  pulsante durante run)

### Warnings (criticidades)

`FindingsListTab` base: header com count + SearchEntry + DropDown de
categorias + ListBox de findings. Cada finding mostra `test_id` +
`message` + `category_label` (traduzido pt-BR).

### Suggestions (melhorias)

Subclasse de FindingsListTab — só sobrescreve `_extract_findings()`
para retornar `report.suggestions` em vez de `report.warnings`.

### Categorias

Agrupa findings por prefixo do `test_id`. Lynis usa prefixos como
`KRNL-5820`, `AUTH-9226`, `BOOT-5122`. Mapping em `backend.CATEGORY_LABELS`
traduz para pt-BR: `KRNL` → "Kernel e sysctl", `AUTH` → "Autenticacao",
`MACF` → "MAC (SELinux/AppArmor)", etc. Cobre ~40 categorias.

## Severidade (escala Lynis)

| Hardening Index | Label | CSS class |
|---|---|---|
| 85-100 | Excelente | `success` |
| 75-84 | Bom | `success` |
| 60-74 | Razoável | `warning` |
| 40-59 | Insuficiente | `error` |
| 0-39 | Crítico | `error` |

## Quando usar

- **Auditoria periódica** (mensal/semestral): demonstrar diligência
  LGPD com Hardening Index + relatório
- **Pós-instalação** de novo serviço: rodar para ver se introduziu
  warnings novas
- **Antes de auditoria externa**: ter snapshot do report como evidência
- **Após hardening manual**: rodar de novo para ver se o índice subiu

## Limitações conhecidas

- Lynis é **read-only** — só reporta, não corrige
- Algumas suggestions podem ser irrelevantes no seu sistema mas Lynis
  ainda lista (ex: "instalar antivírus" mesmo com ClamAV presente). UI
  mostra contador de skipped pra contextualizar
- Sem **comparação temporal** (run1 vs run2) — v0.2 vai trazer
- Parser key=value é robusto mas formatos novos do Lynis podem
  introduzir keys que ignoramos
- Audit demora 2-5 min — UI fica com ProgressBar pulsante (não há
  parsing de progresso real do Lynis em streaming)

## Trecho de código relevante

```python
# backend.py — chmod 640 + chown para LGPD (não world-readable)
raw_user = os.environ.get("USER") or os.environ.get("LOGNAME") or ""
if re.match(r"^[a-z_][a-z0-9_-]{0,31}\$?$", raw_user):
    validated_user = raw_user
else:
    validated_user = ""  # sem chown — apenas chmod
script = """set +e
lynis audit system --quiet --no-colors
rc=$?
if [ -n "$VIGIA_TARGET_USER" ]; then
    chown root:"$VIGIA_TARGET_USER" /var/log/lynis-report.dat 2>/dev/null || true
fi
chmod 640 /var/log/lynis-report.dat 2>/dev/null || true
exit $rc
"""
env = os.environ.copy()
env["VIGIA_TARGET_USER"] = validated_user
result = subprocess.run(
    ["pkexec", "bash", "-c", script],
    capture_output=True, text=True, timeout=600, env=env,
)
```

```python
# backend.py — parser de /var/log/lynis-report.dat
def parse_report(path: Path = REPORT_PATH) -> LynisReport:
    rep = LynisReport()
    if not path.is_file():
        return rep
    text = path.read_text(encoding="utf-8", errors="replace")
    for raw in text.splitlines():
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, _, value = raw.partition("=")
        key, value = key.strip(), value.strip()
        if key == "hardening_index":
            rep.hardening_index = int(value)
        elif key == "warning[]":
            rep.warnings.append(_parse_finding(value))
        elif key == "suggestion[]":
            rep.suggestions.append(_parse_finding(value))
        elif key == "tests_executed":
            rep.tests_executed = len([t for t in value.split("|") if t.strip()])
        # ... + outras keys
    return rep
```
