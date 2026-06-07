# Casca do VigiaOS (rail + seção Hub)

## Em uma frase

Casca (shell) do **VigiaOS** que num único processo GTK4 oferece um **rail de seções** (Início/Hub/Red/Blue), embarca as 14 ferramentas da seção Hub via master-detail (+ Red/Blue pelo mesmo master-detail, via adaptador `Module → ToolEntry`), com tray icon, autostart XDG, password lock via Polkit e auto-lock por inatividade.

## O que envolve

| Item | Valor |
|---|---|
| **Pacotes Linux** | `polkit` (pkexec), `libayatana-appindicator-gtk3` + `gnome-shell-extension-appindicator` (tray opcional) |
| **Comando principal** | `vigia-os` (aliases `vigia-hub`/`vigia-blue`/`vigia-red` abrem o app já na seção) |
| **Permissões** | user para tudo; pkexec apenas para password lock |
| **Stack** | Python 3.11+, PyGObject, GTK4, libadwaita |
| **Path config** | `~/.config/vigia-hub/settings.json` (mode `0600`) |
| **Path autostart** | `~/.config/autostart/vigia-hub.desktop` (XDG) |
| **App ID D-Bus** | `br.com.vigia.OS` |
| **Versão** | 0.6.1 |

## Arquitetura interna

Layout em **3 painéis**:

```
[rail 74px] | [sidebar 280px] | [content flex]
```

O **rail** alterna entre as **seções** (no topo) + atalhos no rodapé:

- `inicio` — landing: monitor do sistema (a tool Dashboard) em tela cheia
- `hub` — vista master-detail das 14 ferramentas registradas
- `red` — módulos de pentest (esqueleto), mesmo master-detail
- `blue` — módulos de SOC, mesmo master-detail
- (rodapé) `settings` — Configurações (view com abas) + sino de Notificações

Em Hub/Red/Blue a sidebar lista os módulos agrupados por categoria — no Hub: `monitoramento`, `privacidade`, `defesa`, `sistema`, `relatorios` (ordem em `registry.CATEGORIES_ORDER`). Red/Blue entram pelo mesmo master-detail via adaptador `Module → ToolEntry`.

Cada `ToolEntry` no `registry.py` declara `embedded_module` (ex: `vigia_dashboard.window`). Quando o user seleciona a tool, a casca faz `importlib.import_module(...)` lazy, chama `build_content()` e embute o widget direto no `Gtk.Stack` da direita. Widgets já construídos são cacheados em `self._embedded_widgets` para preservar estado entre trocas.

Após cada construção de tool, dispara `gc.collect()` para reduzir fragmentação do heap Python (closures temporárias e tooltips de dataclasses).

## Comandos disparados

```bash
# Password lock: dispara o dialog do Polkit nativo do GNOME
pkexec /usr/bin/true

# Tray icon: spawn de subprocess separado (GTK3 nao coexiste com GTK4 num
# mesmo processo PyGObject)
vigia-hub-tray

# Instalacao da lib do tray (chamada pelo dialog do switch, aplica na hora)
pkexec dnf install -y libayatana-appindicator-gtk3 \
                      gnome-shell-extension-appindicator

# Ativa a extensao AppIndicator
gnome-extensions enable appindicatorsupport@rgcjonas.gmail.com
```

A auth usa `pkexec /usr/bin/true` (action default `org.freedesktop.policykit.exec`) — **nenhum** `.policy` custom precisa ser instalado. Em startup chama `subprocess.run` (sync); após o GMainLoop ativo, usa `Gio.Subprocess.communicate_utf8_async` para não bloquear UI nem dar deadlock com a lib Polkit do PyGObject.

## Seções / Funcionalidades

### Seção Hub (e Red/Blue)

Master-detail. Cada `ToolEntry` aparece com ícone, nome, descrição curta, badge de pacotes wrappados (`wrapped_packages`) e dot de status (`success` se `shutil.which` encontra o binário, `error` caso contrário). Red/Blue usam o mesmo widget de lista, com os módulos adaptados de `Module` para `ToolEntry`; o dot de disponibilidade é **por dependência**.

### Configurações (view com abas)

`Adw.ViewSwitcher` com 5 abas, na ordem **Sobre · Atualizações · Aplicação · Segurança · Ajuda**:

- **Sobre** — versão, autor, licença do VigiaOS
- **Atualizações** — embute `vigia_installer.window.build_content()` (ver "Atualizações" abaixo)
- **Aplicação** — autostart, tray, iniciar minimizado, **checar atualizações ao iniciar** (`check_updates`, default ligado)
- **Segurança** — password lock (pkexec), auto-lock por inatividade (5/10/15/30/60 min)
- **Ajuda** — os manuais (ver abaixo)

O switch de tray faz `tray_can_work()` (`checks.py`) que verifica via subprocess se `AyatanaAppIndicator3` importa e se a extensão GNOME `appindicatorsupport@rgcjonas.gmail.com` está `enabled` em `gnome-extensions list --enabled`.

### Aba Ajuda

`Adw.ViewStack` com 3 sub-tabs:

- **Visão geral** — `ExpanderRow` por categoria com `long_description` do registry
- **Manual técnico** — WebKit renderiza `docs/manuals/tecnico/<tool>.md`
- **Manual simples** — WebKit renderiza `docs/manuals/leigo/<tool>.md`

Sem WebKit, cai pra `TextView` monospace com markdown raw.

### Aba Atualizações

Importa `vigia_installer.window.build_content()` e embute na aba.

Ao iniciar, o app roda `vigia_installer.backend.check_updates()` +
`updates_to_notifications()` numa thread (read-only, sem root) e alimenta o
**sininho de notificações** (`NotificationsBell`, de `vigia_common`) no rodapé
do rail — `_apply_update_notifications`. A bolinha vermelha usa o mesmo padrão
do dot de status (`Label("●")` + classe `error`). O toggle `check_updates`
(Configurações → Aplicação) liga/desliga a checagem.

## Quando usar

- Você quer **uma janela só** (um ícone só no menu) ao invés de apps soltos
- Você vai usar a suite diariamente e quer ela na bandeja (tray icon)
- Você precisa de **password lock LGPD** no próprio app
- Você vai dar treinamento e quer acesso aos manuais sem sair da app

## Limitações conhecidas

- Tray icon exige `libayatana-appindicator-gtk3` + extensão GNOME ativada. No Fedora Workstation vanilla **nenhum dos dois** vem instalado; o dialog do switch instala via `dnf` (aplica na hora).
- Idle monitor (`IdleMonitor` em `idle.py`) detecta inatividade da **janela do VigiaOS**, não do sistema. Se o user está usando outra app, ainda conta como idle do VigiaOS — comportamento desejado pra LGPD.
- Em sistema sem `pkexec`, o switch de password lock é silenciosamente revertido com dialog explicativo.
- Schema dconf de tema (`Adw.StyleManager`) só reage corretamente quando a extensão usa `Adw.ColorScheme.PREFER_DARK` / `FORCE_DARK` / `DEFAULT` — alguns DEs antigos podem ignorar.

## Trecho de código relevante

Embarcar tool no painel direito:

```python
# tools/vigia-hub/src/vigia_hub/window.py
def _get_or_build_embedded(self, tool: ToolEntry) -> Gtk.Widget:
    if tool.id in self._embedded_widgets:
        return self._embedded_widgets[tool.id]
    module = importlib.import_module(tool.embedded_module)
    builder = getattr(module, "build_content", None)
    if not callable(builder):
        raise RuntimeError(
            f"{tool.embedded_module}.build_content() nao encontrado"
        )
    widget = builder()
    self._content_stack.add_named(widget, self._embedded_name(tool.id))
    self._embedded_widgets[tool.id] = widget
    gc.collect()
    return widget
```

Auth via pkexec async, sem threads e sem `.policy` custom:

```python
# tools/vigia-hub/src/vigia_hub/auth.py
PKEXEC_CMD = ["pkexec", "/usr/bin/true"]

def check_auth_async(callback):
    proc = Gio.Subprocess.new(
        PKEXEC_CMD,
        Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_PIPE,
    )
    proc.communicate_utf8_async(None, None, on_complete, None)
```
