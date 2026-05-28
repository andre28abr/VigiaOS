# Vigia Hub

## Em uma frase

Launcher mestre da Vigia Suite que embarca todas as 14 ferramentas num único processo GTK4, com tray icon, autostart XDG, password lock via Polkit e auto-lock por inatividade.

## O que envolve

| Item | Valor |
|---|---|
| **Pacotes Linux** | `polkit` (pkexec), `libayatana-appindicator-gtk3` + `gnome-shell-extension-appindicator` (tray opcional) |
| **Comando principal** | `vigia-hub` (script gerado pelo `pyproject.toml`) |
| **Permissões** | user para tudo; pkexec apenas para password lock |
| **Stack** | Python 3.11+, PyGObject, GTK4, libadwaita |
| **Path config** | `~/.config/vigia-hub/settings.json` (mode `0600`) |
| **Path autostart** | `~/.config/autostart/vigia-hub.desktop` (XDG) |
| **App ID D-Bus** | `br.com.vigia.Hub` |
| **Versão** | 0.6.1 |

## Arquitetura interna

Layout em **3 painéis**:

```
[nav fina 74px] | [sidebar 280px] | [content flex]
```

A **nav fina** alterna entre 4 modos:

- `tools` — vista master-detail das tools registradas
- `installer` — embute o Tool Installer fullscreen
- `settings` — Configurações globais do Hub
- `help` — Manuais com `WebKit 6.0` renderizando os `.md` desta pasta

Em modo `tools`, a sidebar lista as ferramentas agrupadas pelas categorias `monitoramento`, `privacidade`, `defesa`, `sistema`, `relatorios` (ordem definida em `registry.CATEGORIES_ORDER`).

Cada `ToolEntry` no `registry.py` declara `embedded_module` (ex: `vigia_dashboard.window`). Quando o user seleciona a tool, o Hub faz `importlib.import_module(...)` lazy, chama `build_content()` e embute o widget direto no `Gtk.Stack` da direita. Widgets já construídos são cacheados em `self._embedded_widgets` para preservar estado entre trocas.

Após cada construção de tool, dispara `gc.collect()` para reduzir fragmentação do heap Python (closures temporárias e tooltips de dataclasses).

## Comandos disparados

```bash
# Password lock: dispara o dialog do Polkit nativo do GNOME
pkexec /usr/bin/true

# Tray icon: spawn de subprocess separado (GTK3 nao coexiste com GTK4 num
# mesmo processo PyGObject)
vigia-hub-tray

# Instalacao da lib do tray em Silverblue (chamada pelo dialog do switch)
pkexec rpm-ostree install libayatana-appindicator-gtk3 \
                          gnome-shell-extension-appindicator

# Ativa a extensao AppIndicator
gnome-extensions enable appindicatorsupport@rgcjonas.gmail.com
```

A auth usa `pkexec /usr/bin/true` (action default `org.freedesktop.policykit.exec`) — **nenhum** `.policy` custom precisa ser instalado. Em startup chama `subprocess.run` (sync); após o GMainLoop ativo, usa `Gio.Subprocess.communicate_utf8_async` para não bloquear UI nem dar deadlock com a lib Polkit do PyGObject.

## Tabs / Funcionalidades

### Modo Tools

Master-detail. Cada `ToolEntry` aparece com ícone, nome, descrição curta, badge de pacotes wrappados (`wrapped_packages`) e dot de status (`success` se `shutil.which` encontra o binário, `error` caso contrário).

### Modo Configurações

Três sub-abas via `Adw.ViewSwitcher`:

- **Aplicação** — autostart, tray, iniciar minimizado, tema (system/light/dark)
- **Segurança** — password lock (pkexec), auto-lock por inatividade (5/10/15/30/60 min)
- **Sobre** — paths dos arquivos de config e versão

O switch de tray faz `tray_can_work()` (`checks.py`) que verifica via subprocess se `AyatanaAppIndicator3` importa e se a extensão GNOME `appindicatorsupport@rgcjonas.gmail.com` está `enabled` em `gnome-extensions list --enabled`.

### Modo Ajuda

`Adw.ViewStack` com 3 sub-tabs:

- **Visão geral** — `ExpanderRow` por categoria com `long_description` do registry
- **Manual técnico** — WebKit renderiza `docs/manuals/tecnico/<tool>.md`
- **Manual simples** — WebKit renderiza `docs/manuals/leigo/<tool>.md`

Sem WebKit, cai pra `TextView` monospace com markdown raw.

### Modo Instalador

Importa `vigia_installer.window.build_content()` e embute fullscreen.

## Quando usar

- Você quer **uma janela só** ao invés de 14 atalhos no menu de apps
- Você vai usar a suite diariamente e quer ela na bandeja (tray icon)
- Você precisa de **password lock LGPD** no próprio launcher
- Você vai dar treinamento e quer acesso aos manuais sem sair da app

## Limitações conhecidas

- Tray icon exige `libayatana-appindicator-gtk3` + extensão GNOME ativada. Em Silverblue vanilla **nenhum dos dois** vem instalado e a lib precisa de reboot (overlay rpm-ostree).
- Idle monitor (`IdleMonitor` em `idle.py`) detecta inatividade da **janela do Hub**, não do sistema. Se o user está usando outra app, ainda conta como idle do Hub — comportamento desejado pra LGPD.
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
