# Vigia Privacy Controls

> App GTK4 com painel central de toggles de privacidade.
> Complementa o **Vigia Activity Log**: ele observa o que aconteceu,
> este configura o que é permitido.

## Estado

🟡 **v0.1** — MVP funcional com 3 toggles em user-scope.

| Toggle | Categoria | Mecanismo |
|---|---|---|
| Serviços de localização | Localização | dconf `org.gnome.system.location enabled` |
| Bloquear relatórios técnicos | Telemetria | dconf `org.gnome.desktop.privacy report-technical-problems` (invertido) |
| Bluetooth | Dispositivos | `bluetoothctl power on/off` |

## Setup na VM (Silverblue)

PyGObject e libadwaita ja vem com GNOME no Silverblue. Se faltar:
```bash
sudo rpm-ostree install python3-gobject libadwaita
systemctl reboot
```

### Opcao A — rodar direto sem instalar (mais rapido para testar)

O pacote esta em `src/` (layout "src" do Python), entao precisa setar `PYTHONPATH`:

```bash
cd ~/dev/VigiaOS/tools/privacy-controls
PYTHONPATH=src python -m vigia_privacy
```

### Opcao B — instalar editable (recomendado para uso continuo)

```bash
cd ~/dev/VigiaOS/tools/privacy-controls
pip install --user -e .
vigia-privacy           # script criado pelo entry point
```

Modo editable: mudancas em src/ refletem na proxima execucao sem precisar
reinstalar. Para desinstalar: `pip uninstall vigia-privacy-controls`.

## Arquitetura

```
src/vigia_privacy/
├── __init__.py        # __version__, __app_id__
├── __main__.py        # entrypoint (python -m vigia_privacy)
├── app.py             # Adw.Application
├── window.py          # janela + render dos toggles
└── toggles/
    ├── __init__.py    # registra ALL_TOGGLES (ordem visual)
    ├── base.py        # dataclass Toggle (interface comum)
    ├── location.py    # GNOME location services
    ├── telemetry.py   # GNOME usage reporting
    └── bluetooth.py   # bluetoothctl power
```

### Adicionar um toggle novo

1. Crie `src/vigia_privacy/toggles/<nome>.py`:
   ```python
   from .base import Toggle

   def _get(): ...
   def _set(value): ...
   def _available(): ...

   TOGGLE = Toggle(
       name="Rotulo curto",
       description="Explicacao 1-2 linhas",
       category="Localizacao | Telemetria | Dispositivos | Rede | ...",
       get_fn=_get,
       set_fn=_set,
       available_fn=_available,
   )
   ```
2. Importe em `toggles/__init__.py` e adicione à lista `ALL_TOGGLES`.

### Toggles em system-scope (futuro v0.2)

Toggles que mudam estado fora do user (firewall, DNS, systemctl) precisam
de **polkit**. A v0.2 vai adicionar:

- Helper service em D-Bus (system bus) com polkit policy
- O app cliente chama via `Gio.DBusProxy`
- pkexec dialogo para autenticacao

Toggles previstos para v0.2:
- Firewall (firewalld zone trusted vs strict)
- DNS over TLS (`/etc/systemd/resolved.conf`)
- SSH server (`systemctl enable/disable ssh`)
- Tor (`systemctl start/stop tor`)

## Por que Python + PyGObject?

- Iteração visual rápida (vs Rust gtk-rs)
- Ecossistema rico de integração D-Bus / dconf / systemctl
- Stack que GNOME usa para apps oficiais (Settings, Software, ...)
- Bind nativo do libadwaita (não precisa de wrapper)

## Lint local

```bash
pip install --user ruff
ruff check src/
```
