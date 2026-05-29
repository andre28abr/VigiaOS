# Vigia Hub

> Launcher mestre do **VigiaOS**. Em vez de cada ferramenta ter seu próprio
> ícone no menu do GNOME, o Hub aparece como um único app que lista todas as
> ferramentas disponíveis e lança cada uma com um clique.

## Estado

🟡 **v0.1 MVP** — registra Activity Log e Privacy Controls. Detecta automaticamente
quais estão instaladas (via `shutil.which()` no binário).

## Como funciona

`src/vigia_hub/registry.py` contém uma lista `TOOLS` de `ToolEntry`. Cada entry sabe:
- `id`, `name`, `description`, `icon`
- `exec_cmd`: comando para spawnar
- `needs_terminal`: True para CLI tools (abre em gnome-console/ptyxis/etc.)
- `needs_root`: True para tools que precisam sudo
- `available_fn`: lambda que checa se o binário existe

Window mostra cada tool como `Adw.ActionRow` com ícone, descrição e botão "Abrir".
Click no botão chama `subprocess.Popen` com os wrappers apropriados:
- `needs_root=True` → prefix `sudo`
- `needs_terminal=True` → prefix `<terminal-binary> --`

Terminais procurados em ordem: `kgx`, `ptyxis`, `gnome-terminal`, `konsole`, `xterm`, `alacritty`.

## Adicionar uma ferramenta nova

Em `src/vigia_hub/registry.py`, append:

```python
ToolEntry(
    id="selinux-gui",
    name="SELinux GUI",
    description="Gerenciador moderno de policies SELinux",
    icon="br.com.vigia.SelinuxGui",
    exec_cmd=["vigia-selinux"],
    needs_terminal=False,
    needs_root=False,  # internal pkexec, nao precisa sudo no launch
    available_fn=lambda: shutil.which("vigia-selinux") is not None,
),
```

Salva. Reabre o Hub. Aparece automaticamente.

## Setup na VM

```bash
cd ~/dev/VigiaOS/tools/vigia-hub
pip install --user -e .

# Instalar entry no menu GNOME
mkdir -p ~/.local/share/applications ~/.local/share/icons/hicolor/scalable/apps
cp data/br.com.vigia.Hub.desktop ~/.local/share/applications/
cp data/br.com.vigia.Hub.svg ~/.local/share/icons/hicolor/scalable/apps/
update-desktop-database ~/.local/share/applications 2>/dev/null || true
```

Aperta Super, digita "Vigia Hub". Apenas **1 entry** aparece no menu, em vez
de uma por ferramenta. Cada tool é lançada de dentro do Hub.

## Roadmap

- v0.2: status de cada tool (versão instalada, última execução)
- v0.3: integração via `gio launch <app-id>` (respeita Terminal=true do .desktop, mais portavel)
- v0.4: settings global da suite (tema, fonte, paths)
- v0.5: notificações desktop quando tools terminam tarefas longas
