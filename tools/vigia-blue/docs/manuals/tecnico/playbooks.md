# Vigia Playbooks — manual técnico

Módulo de **Resposta a Incidentes** do **VigiaBlue**. Diferente dos demais, **não
envolve ferramenta externa**: é **conteúdo + checklist + trilha**. Traz playbooks
de IR prontos (contenção → erradicação → recuperação → notificação), o operador
marca os passos e adiciona notas, e o módulo salva um **registro de atendimento**
datado (0600) — a trilha que a LGPD (art. 48) e a boa prática de SOC exigem.

## Arquivos

```
tools/vigia-blue/src/vigia_blue/modules/playbooks/
├── __init__.py
├── backend.py     # catálogo + estado + trilha (PURO/testável)
└── page.py        # GUI: Playbooks (checklist) / Histórico / Sobre

tests/blue/test_playbooks_backend.py   # 12 testes
tools/vigia-blue/docs/manuals/{leigo,tecnico}/playbooks.md
```

## Backend (`backend.py`) — tudo puro/testável

Modelo: `Step(text, detail)` → `Phase(name, steps)` → `Playbook(id, title, when,
severity, phases)`. Um atendimento é um `Incident(playbook_id, playbook_title,
started_at, done_steps[], notes, closed)`.

Catálogo (`playbooks()`): **5 playbooks** pt-BR — `intrusao`, `lgpd_vazamento`,
`ransomware`, `conta_comprometida`, `malware`. Conteúdo escrito para leigo, com
`detail` explicando o "porquê" dos passos críticos.

Estado (puro):
- **`step_key(pi, si)`** → `"fase.passo"` (chave estável do passo).
- **`start_incident(pb)`** → novo `Incident` com timestamp.
- **`toggle_step(inc, key)`** → marca/desmarca.
- **`progress(inc, pb)`** → `(cumpridos, total)`, contando **só chaves válidas**
  do playbook (ignora chave obsoleta se o roteiro mudar).

Trilha (0600, via `vigia_common.state`):
- **`save_incident(inc)`** → `~/.local/share/vigia-playbooks/incident-<ts>.json`.
- **`list_incidents(limit)`** → mais novos primeiro, descarta corrompidos.

## GUI (`page.py`)

`build_content()` → `Adw.ToolbarView` + `ViewSwitcher` (abas Playbooks/Histórico/
Sobre). Cada playbook é um **`_PlaybookExpander`** (subclasse de `Adw.ExpanderRow`):
título + "quando usar" + pílula de severidade; ao expandir, mostra as fases
(cabeçalho `heading`) e os passos como `ActionRow` com `Gtk.CheckButton` (o
próprio row é `activatable_widget` do check). No fim: `Adw.EntryRow` de notas +
botão **Registrar** → monta o `Incident` a partir dos checks marcados, calcula
`progress`, marca `closed` se 100%, e salva. **Histórico** lista
`list_incidents()`. Severidade: mesma escala dos outros módulos.

## Privilégio / LGPD

- Roda **sem root** — só lê/escreve no diretório do usuário.
- Registros **0600**; nada sai da máquina. É a **trilha de auditoria** de
  resposta a incidente (prova de diligência sob a LGPD art. 48).

## Pendências (próximos passos)

1. Retomar um atendimento em aberto (carregar `Incident` salvo de volta na UI).
2. Exportar o atendimento como PDF (sinergia com o módulo Reports do Hub).
3. Playbooks personalizados do usuário (carregar de um diretório).
