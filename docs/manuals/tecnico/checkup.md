# Tudo Certo? (checkup)

## Em uma frase

Painel de **postura de segurança** embarcado no VigiaOS (`vigia_hub.checkup`)
que agrega `vigia_common.posture` num semáforo 🟢🟡🔴 — checa atualizações,
firewall, antivírus e privacidade — com botão **Resolver** que navega pra
ferramenta certa via Gio actions.

## O que envolve

| Item | Detalhe |
|---|---|
| Módulo | `vigia_hub.checkup` (GUI) + `vigia_common.posture` (lógica) |
| Categoria no Hub | **Visão geral** (1ª tool do Hub) |
| Comandos | `systemctl is-active firewalld`, `dnf --cacheonly check-update`, `gsettings get …`, leitura de mtime da base ClamAV |
| Privilégios | **Nenhum** — tudo read-only sem root |
| Navegação | Gio actions `show-tool` / `show-tool-tab` / `show-settings` do app |
| Execução | Checagens rodam em `threading.Thread` (não bloqueia a UI) |
| Versão | vigia-hub 0.11.x |

## Arquitetura interna

Duas camadas:

```
vigia_common/posture.py     — avaliadores PUROS + coletores (sem GTK)
vigia_hub/checkup.py        — controller GUI (hero + lista + Resolver)
```

A separação segue o padrão Vigia: **avaliadores puros** (`eval_firewall`,
`eval_updates`, `eval_antivirus`, `eval_privacy`) recebem valores já
coletados e devolvem um `Check` — testáveis sem tocar no sistema. Os
**coletores** (`gather_*`) é que rodam subprocess / leem o filesystem.

`posture.Check` (frozen dataclass):

```python
@dataclass(frozen=True)
class Check:
    key: str            # "firewall"
    label: str          # "Firewall"
    status: str         # ok | warn | bad | unknown
    detail: str         # frase curta pro usuário
    fix_tool: str = ""  # id de tool pra "Resolver" (vazio = sem botão)
    fix_label: str = ""  # rótulo do botão ("Ligar firewall")
```

`posture.run_all()` coleta e devolve a lista `[updates, firewall, antivirus,
privacy]`. `overall_status(checks)` calcula o **pior** status (ordem
`ok < unknown < warn < bad`) — é o que pinta o hero do semáforo.

## As 4 verificações

| Check | Coletor | Critério |
|---|---|---|
| **Atualizações** | `gather_updates()` → `dnf -q --cacheonly check-update` | rc 0 = em dia; rc 100 = conta linhas de pacote → WARN |
| **Firewall** | `gather_firewall()` → `systemctl is-active firewalld` | `active` = OK; senão BAD |
| **Antivírus** | `gather_antivirus()` → mtime de `*.cvd`/`*.cld` em `/var/lib/clamav` (+dirs) | base ≤ 7 dias = OK; >7d ou ausente = WARN; ClamAV não instalado = WARN |
| **Privacidade** | `gather_privacy()` → `gsettings get` de 4 chaves GNOME | todas endurecidas = OK; senão WARN com a contagem do que falta |

Chaves de privacidade verificadas (`posture._PRIVACY_KEYS`):
`org.gnome.desktop.privacy report-technical-problems`,
`org.gnome.system.location enabled`,
`org.gnome.desktop.privacy send-software-usage-stats`,
`org.gnome.desktop.privacy remember-recent-files` — todas esperadas em
`false`. Chaves ausentes na versão do GNOME não contam pro total.

`gather_updates` usa `--cacheonly` de propósito: é **rápido e sem rede**
(pode estar levemente desatualizado, mas não trava abrindo o painel).

## Fluxo da GUI

```python
# checkup.py — re-checa toda vez que a tela aparece
self.toolbar.connect("map", lambda *_a: self._run())

def _run(self):
    # set hero "Verificando…" + spinner, dispara thread
    threading.Thread(target=self._worker, daemon=True).start()

def _worker(self):
    checks = posture.run_all()
    GLib.idle_add(self._render, checks)
```

- O `connect("map", …)` garante o **re-check ao reexibir** — sem cache
  preso (ex: voltou depois de atualizar a base do antivírus → o semáforo
  reflete o novo estado).
- `_render` monta o hero (ícone+título+descrição via `_OVERALL[status]`) e
  uma `Adw.ActionRow` por `Check`, com um `dot` colorido (`success` /
  `warning` / `error` / `dim-label`) como prefixo.
- O botão **Resolver** só é adicionado se `c.fix_tool` existe **e**
  `c.status != OK`.

## Navegação do "Resolver"

O botão dispara `app.activate_action(...)` conforme o formato de `fix_tool`:

```python
def _on_fix(self, _btn, fix_tool):
    app = Gio.Application.get_default()
    if fix_tool == "config":
        app.activate_action("show-settings", None)
    elif ":" in fix_tool:  # "toolid:aba" → abre a tool já na aba certa
        app.activate_action("show-tool-tab", GLib.Variant.new_string(fix_tool))
    elif fix_tool:
        app.activate_action("show-tool", GLib.Variant.new_string(fix_tool))
```

Mapeamento (de `posture.eval_*`):

| Situação | `fix_tool` | Ação |
|---|---|---|
| Firewall desligado | `firewall-gui` | `show-tool` → Firewall |
| Base de vírus velha | `antivirus:database` | `show-tool-tab` → Antivírus, aba *Base de dados* |
| ClamAV ausente | `antivirus` | `show-tool` → Antivírus |
| Atualizações pendentes | `config` | `show-settings` → Configurações (Atualizações) |
| Privacidade a ajustar | `privacy-controls` | `show-tool` → Controles de Privacidade |

## Reuso: status no card do Hub

`posture` também alimenta o **status curto** no card de cada ferramenta do
Hub (`ToolEntry.status_fn`), via funções de 1-2 palavras:

- `status_firewall()` → `"ligado"` / `"desligado"`
- `status_antivirus()` → `"base em dia"` / `"base de 14d"` / `"sem base"` / `"não instalado"`
- `status_privacy()` → `"ok"` / `"2 a ajustar"`

São preenchidas em thread no Hub (`_load_section_statuses`).

## Quando usar

- **Triagem rápida**: "está tudo seguro?" sem abrir 4 ferramentas.
- **Pós-mudança**: confirmar que firewall/privacidade seguem ativos depois
  de mexer no sistema.
- **Ponto de partida**: usar os botões Resolver como atalho pra a tool
  certa quando algo está fora do lugar.

## Limitações conhecidas

- `dnf --cacheonly` pode reportar contagem **levemente desatualizada** (não
  faz refresh de metadados; é trade-off por velocidade).
- Detecta **firewalld** especificamente — outros firewalls (ufw, nftables
  puro) aparecem como "não consegui verificar" (UNKNOWN).
- Privacidade cobre **4 chaves** GNOME (subconjunto do que o Privacy
  Controls oferece) — é um indicador, não a auditoria completa.
- Sem `systemctl`/`dnf`/`gsettings` no PATH, a checagem correspondente cai
  pra UNKNOWN (não derruba o painel).

## Referências

- `vigia_common/posture.py`, `vigia_hub/checkup.py`
- DEVELOPMENT.md §9, entrada *2026-06-09 — Facilidade & funcionalidade*
