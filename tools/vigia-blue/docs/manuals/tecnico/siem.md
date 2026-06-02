# Vigia SIEM — manual técnico

Módulo de **Detecção & SIEM** do **VigiaBlue**. É uma **camada de detecção**
sobre o core do Activity Log (binário Rust `vigia-log`): coleta o mesmo bundle
de eventos (audit/journald/fail2ban) e aplica **regras de detecção** que geram
**alertas** triados por severidade — cada um com texto leigo + recomendação.

> **Estado atual (2026-06-01):** backend + GUI prontos. **2º módulo "pronto"**
> do ecossistema (depois do Vigia YARA). Abas Alertas/Regras/Histórico/Sobre
> (`page.py`) ligadas ao shell via `Module.impl`.

## Diferença para o Activity Log (por que não é redundante)

| | Activity Log (Hub) | Vigia SIEM (Blue) |
|---|---|---|
| Papel | Navegador / timeline | Camada de **detecção** |
| Pergunta | "o que aconteceu?" | "o que é **suspeito**?" |
| Saída | lista de eventos | **alertas** por regra, com recomendação |
| Fonte | `vigia-log` | **o mesmo** `vigia-log` |

É exatamente como uma stack de SOC real separa *log aggregation* de *SIEM/detection*.

## Arquivos

```
tools/vigia-blue/
└── src/vigia_blue/modules/siem/
    ├── __init__.py     # mínimo (sem gi — mantém backend testável)
    ├── backend.py      # parser + MOTOR de regras + coleta + relatórios (PURO/testável)
    └── page.py         # GUI: build_content() → abas Alertas/Regras/Histórico/Sobre

tests/blue/test_siem_backend.py   # 36 testes (parser, helpers, 7 regras, motor, catálogo, relatórios)
tools/vigia-blue/docs/manuals/{leigo,tecnico}/siem.md
```

## Dependência

- O binário **`vigia-log`** (core do Activity Log, escrito em Rust). É o
  **artefato compartilhado** — o VigiaBlue **não** importa o pacote Python
  `vigia_log_gui`, só chama o binário no PATH. `core_available()` =
  `shutil.which("vigia-log")`. Sem ele, a GUI mostra banner + instruções
  (`core_install_hint()`), sem quebrar.
- O `audit` exige privilégio → coleta opcional via **pkexec** (switch na UI).

## Fluxo de dados

```
vigia-log --output json-bundle --sources journald fail2ban [audit]
        │  (JSON: {events:[{timestamp,source,severity,narrative,payload}], correlations:[…]})
        ▼
collect()  →  parse_bundle()  →  list[Event]
        ▼
detect(events, correlations)  →  list[Alert]   (ordenado por severidade desc)
        ▼
SiemResult  →  save_report() (~/.local/share/vigia-siem/analysis-*.json, 0600)
```

O **`source`** do evento vem do core como `"audit"` / `"journal"` / `"fail2ban"`
(atenção: `"journal"`, não `"journald"` — este último é só o nome da *fonte* no
argumento `--sources`).

## Backend (`backend.py`)

Partes **puras** (testadas sem `vigia-log` nem gi):

- **`parse_bundle(data) -> (events, correlations)`** — converte o JSON em
  `list[Event]` + `list[dict]`. Defensivo (nunca crasha com JSON inesperado).
- **`detect(events, correlations=None) -> list[Alert]`** — o **motor**: roda
  cada regra de `_MATCHERS`, anexa correlações do core como alertas, e ordena por
  `SEVERITY_RANK` (desc). Uma regra que levante exceção é **ignorada** (não
  derruba a análise).
- **`rules_catalog() -> list[Rule]`** — metadados das 7 regras (p/ a aba Regras).
- Helpers de leitura do `payload` (`_audit_field`, `_audit_primary_type`,
  `_is_failure`, `_msg`, `_comm`, `_f2b_action`, …) — defensivos.

Parte que toca o sistema:

- **`collect(sources, elevated, limit, timeout) -> (data|None, erro)`** — roda
  `vigia-log` via `vigia_common.proc.run` (nunca levanta). argv em **lista**,
  `pkexec` como prefixo quando `elevated` (NUNCA shell string). Trata
  `rc in (126,127)` = auth cancelada, JSON malformado, etc.
- **`analyze(...) -> SiemResult`** — orquestra collect + parse + detect + tempo.

Relatórios (padrão Vigia YARA, via `vigia_common.state`):

- **`save_report(result)`** → `~/.local/share/vigia-siem/analysis-<ts>.json`,
  escrita atômica **0600** (LGPD — pode conter IPs/usuários).
- **`list_recent_reports(limit)`** → mais novos primeiro, descarta corrompidos.

## As 7 regras de detecção

Cada regra é uma função pura `(events) -> list[Alert]`, registrada em `_MATCHERS`
e descrita em `RULES` (catálogo). Limiares em constantes no topo.

| id | nome | fonte | severidade | dispara quando |
|---|---|---|---|---|
| `ssh_bruteforce` | Força-bruta de login | audit, journal | alto/crítico | ≥5 falhas de auth da mesma origem (≥20 → crítico). Agrupa por IP/host/conta. |
| `failed_sudo` | Falha de elevação | audit, journal | suspeito/alto | sudo/su com `res=failed` ou PAM "authentication failure" (≥5 → alto). |
| `account_change` | Conta criada/alterada | audit, journal | suspeito | record types `ADD_USER`/`USER_MGMT`/… ou comm `useradd`/`usermod`/… |
| `service_failure` | Falha de serviço | journal, audit | baixo/suspeito | "Failed to start"/"entered failed state" ou unidade `.service` com prio ≥err (≥10 → suspeito). |
| `selinux_denial` | Bloqueio do SELinux | audit | suspeito/baixo | AVC; `permissive=0` → suspeito (enforcing), senão baixo. 2 alertas separados. |
| `package_change` | Software instalado/removido | journal | info | comm `rpm-ostree`/`dnf`/`flatpak`/… ou msg "Installed:"/"Removed:"/"Upgraded:". |
| `fail2ban_ban` | IP bloqueado | fail2ban | suspeito | `action.kind == "ban"`; lista IPs e jails distintos. |

**Correlações do core**: o `vigia-log` já emite `correlations[]` (padrões
cross-source). `detect()` mapeia cada uma para um `Alert` (`rule_id="correlation"`),
traduzindo a severidade (`suspicious→suspeito`, `interesting→baixo`,
`routine→info`).

> **Limites (honestos):** a contagem é **dentro da janela coletada** (`--limit`,
> default 800), não uma janela deslizante por minuto — força-bruta espalhada por
> dias num bundle grande poderia somar. Os limiares são conservadores e ajustáveis;
> janela temporal real fica para a v0.2.

## GUI (`page.py`)

`build_content()` retorna um `Adw.ToolbarView` auto-contido (header com
`Adw.ViewSwitcher` + `Adw.ViewStack`):

- **Alertas** (`_AlertsView`): switch "Incluir o log de auditoria (audit)"
  (→ `elevated`, adiciona a fonte `audit`), botão **Analisar agora** (fora de
  card), banner se o `vigia-log` faltar. A análise roda em `threading.Thread` →
  `GLib.idle_add`. **Cada alerta é um `Adw.ExpanderRow`** (helper `_sev_expander`):
  recolhido mostra título + severidade colorida; expandido mostra **O que é**,
  **O que fazer**, **Quando**, **Ocorrências** e **Evidência (técnico)**. Resumo
  no topo (`N alerta(s) (x alto · y suspeito …) · M evento(s) · tempo`).
- **Regras** (`_build_rules`): lista o `rules_catalog()` — 1 `ExpanderRow` por
  regra (nome, descrição, pílula de severidade; expande O que fazer / Categoria /
  Fontes). É onde o leigo aprende o que é detectado.
- **Histórico** (`_HistoryView`): `list_recent_reports()` → 1 linha por análise.
- **Sobre**: descrição + a diferença para o Activity Log + como instalar o core.

Escala de severidade (`_SEVERITY`): `info`/`baixo` (accent) · `suspeito` (warning)
· `alto`/`critico` (error) — mesma do Vigia YARA + `info`.

## Privilégio / LGPD

- Sem `audit`, roda **sem root** (journald do usuário + fail2ban).
- Com `audit`, **pkexec** (argv-list) — UM diálogo polkit por análise.
- Relatórios **0600**; nada sai da máquina (offline por princípio). O módulo só
  **lê** logs, não altera nada.

## Pendências (próximos passos)

1. **Janela temporal** real (sliding window por minuto) na força-bruta.
2. **Regras do usuário** (carregar definições extras de um diretório).
3. **Notificação** (libnotify) quando uma análise agendada achar algo crítico.
4. Empacotar p/ instalação não-editable + spec COPR.
