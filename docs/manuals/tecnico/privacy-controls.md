# Privacy Controls

## Em uma frase

Painel com 12 toggles de privacidade que mapeiam direto pra chaves `dconf`, units `systemd` e `bluetoothctl`, eliminando a necessidade de editar `gsettings`, `/etc/selinux/config` ou `systemctl` manualmente.

## O que envolve

| Item | Valor |
|---|---|
| **Pacotes Linux** | `dconf` + `glib2` (Gio.Settings), `systemctl` (systemd), `bluez` (bluetoothctl) opcional |
| **Comando principal** | `Gio.Settings.new(schema).set_boolean(key, value)` + `pkexec systemctl enable/disable --now <unit>` |
| **Permissões** | user para dconf (10 toggles); **pkexec** para systemd (2 toggles) |
| **Stack** | Python 3.11, PyGObject, GTK4, libadwaita |
| **Path config** | Nenhum config próprio — estado vive no dconf do usuário e no systemd |
| **Path dados** | `~/.config/dconf/user` (binário gerenciado pelo sistema) |
| **App ID** | `br.com.vigia.PrivacyControls` |
| **Versão** | 0.3.2 |

## Arquitetura interna

Padrão **Toggle factory**:

- `toggles/base.py` define `dataclass Toggle` com `get_fn`, `set_fn`, `available_fn`.
- `dconf_toggle(schema, key, ..., invert)` cria toggle user-scope que faz `Gio.Settings.new(schema).get_boolean(key)` / `set_boolean(key, value)`. Flag `invert=True` quando a semântica do dconf inverte ("remember-X = true" vs "Nao lembrar X = true").
- `systemd_unit_toggle(unit, ...)` cria toggle system-scope. Leitura via `systemctl is-active <unit>` (sem privilégio). Escrita via `pkexec systemctl enable/disable --now <unit>.service`.
- `bluetooth.py` cria toggle ad-hoc via `bluetoothctl power on|off`.

`ALL_TOGGLES` em `toggles/__init__.py` lista os 12 toggles na ordem visual. A janela agrupa por `category` em `Adw.PreferencesGroup`s.

A coleta de estado inicial roda em **`threading.Thread`** por toggle (paraleliza `systemctl is-active` x2 + `bluetoothctl show` sem bloquear UI thread no startup). Switches começam `sensitive=False` até o worker terminar e chamar `GLib.idle_add(_apply_toggle_state, ...)`.

## Comandos disparados

```bash
# User-scope (sem senha) — 10 toggles
# Equivalente a:
gsettings set org.gnome.system.location enabled false
gsettings set org.gnome.desktop.privacy report-technical-problems false
# (etc — fica em ~/.config/dconf/user, binario)

# System-scope (1 dialog pkexec por toggle)
pkexec systemctl enable  --now firewalld.service
pkexec systemctl disable --now sshd.service

# Bluetooth (sem pkexec — bluetoothctl tem polkit proprio)
bluetoothctl power on
bluetoothctl power off
```

## Tabs / Funcionalidades

Apenas 2 tabs (`ViewSwitcher`): **Toggles** e **Sobre**.

### Toggles — agrupados por categoria

**Localização**
- `Serviços de localização` — schema `org.gnome.system.location` / key `enabled`

**Telemetria**
- `Bloquear relatórios técnicos do GNOME` — schema `org.gnome.desktop.privacy` / `report-technical-problems` (invertido)

**Histórico** (rastros locais)
- `Não lembrar arquivos recentes` — `org.gnome.desktop.privacy/remember-recent-files` (invertido)
- `Não lembrar uso de aplicativos` — `.../remember-app-usage` (invertido)
- `Esconder identidade em arquivos compartilhados` — `.../hide-identity`

**Lock Screen**
- `Bloquear tela automaticamente` — `org.gnome.desktop.screensaver/lock-enabled`
- `Esconder prévia de notificações na lock screen` — `org.gnome.desktop.notifications/show-in-lock-screen` (invertido)

**Limpeza Automática**
- `Esvaziar lixeira automaticamente` — `.../remove-old-trash-files`
- `Limpar arquivos temporários automaticamente` — `.../remove-old-temp-files`

**Rede** (system-scope, **pkexec**)
- `Firewall (firewalld)` — `pkexec systemctl enable/disable --now firewalld.service`
- `Servidor SSH (sshd)` — `pkexec systemctl ... sshd.service`

**Dispositivos**
- `Bluetooth` — `bluetoothctl power on/off` (só aparece se `bluetoothctl list` retorna controller)

### Indisponibilidade

Toggles cuja `available_fn()` retorna `False` ficam `set_sensitive(False)` com subtitle `[indisponivel neste sistema]`. Casos comuns: schema dconf não instalado (KDE), unit `sshd.service` ausente, máquina sem adapter Bluetooth.

### Sobre

Versão + lista de pacotes wrappados (`dconf`, `systemctl`) + onde ficam os dados (`~/.config/dconf/user`).

## Quando usar

- Você **acabou de instalar** o Fedora Workstation e quer ajustar privacidade em **um lugar só** (em vez de Settings + dconf-editor + systemctl)
- Você vai usar a máquina em escritório com LGPD e precisa ligar firewall + esconder notificações na lock screen
- Você quer demonstrar para auditoria que telemetria GNOME está off
- Você vai conectar em rede pública e quer **desligar SSH** + ligar **firewall** rápido

## Limitações conhecidas

- Mudanças em dconf são sincronizadas com GNOME Settings em tempo real — abrir os dois ao mesmo tempo dá pra ver os switches mudando juntos.
- Toggles system-scope pedem senha **a cada mudança** (sem persistência de auth).
- Em GNOME mais novo (45+), algumas chaves foram movidas/renomeadas. `available_fn` checa via `SettingsSchemaSource.lookup(schema).has_key(key)` e dimma o switch se não existir.
- Bluetooth depende de `bluetoothctl` — se o sistema usa apenas o stack do GNOME Settings via D-Bus, pode haver delay de 1-2s pra ver o switch.

## Trecho de código relevante

Factory de toggle dconf com semântica invertida:

```python
# tools/privacy-controls/src/vigia_privacy/toggles/base.py
def dconf_toggle(*, schema, key, name, description, category, invert=False):
    def _get() -> bool:
        raw = Gio.Settings.new(schema).get_boolean(key)
        return (not raw) if invert else raw

    def _set(value: bool) -> None:
        stored = (not value) if invert else value
        Gio.Settings.new(schema).set_boolean(key, stored)

    def _available() -> bool:
        src = Gio.SettingsSchemaSource.get_default()
        schema_obj = src.lookup(schema, recursive=True)
        return schema_obj is not None and schema_obj.has_key(key)

    return Toggle(name=name, description=description, category=category,
                  get_fn=_get, set_fn=_set, available_fn=_available)
```

Toggle systemd com pkexec async:

```python
# tools/privacy-controls/src/vigia_privacy/toggles/base.py
def _set(value: bool) -> None:
    if shutil.which("pkexec") is None:
        raise RuntimeError("pkexec nao encontrado.")
    action = "enable" if value else "disable"
    result = subprocess.run(
        ["pkexec", "systemctl", action, "--now", f"{unit}.service"],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        if "Request dismissed" in stderr or result.returncode == 126:
            raise RuntimeError("Autenticacao cancelada pelo usuario.")
        raise RuntimeError(f"systemctl {action} --now {unit} falhou: {stderr}")
```
