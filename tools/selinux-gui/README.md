# Vigia SELinux GUI

> Gerenciador moderno em GTK4 + libadwaita para SELinux. Substituto visual do
> `system-config-selinux` (que ainda é GTK2).

## Estado

🟡 **v0.1 MVP** — duas tabs:

### Status
- Modo atual (Enforcing / Permissive / Disabled) com cor semântica
- Política ativa (`targeted` etc.)
- Versão da política
- Switch Enforcing/Permissive — muda runtime via `pkexec setenforce`
- Botão "Atualizar" para re-ler estado

### Booleans
- Lista completa dos SELinux booleans (`getsebool -a`, ~300 entries em Fedora)
- Search bar com filtro incremental por nome
- Switch por boolean — muda persistente via `pkexec setsebool -P`
- Erro dialog se setsebool falhar (ex: boolean read-only)

## Setup

```bash
cd ~/dev/VigiaOS/tools/selinux-gui
pip install --user -e .
vigia-selinux
```

Para instalar no menu GNOME:
```bash
mkdir -p ~/.local/share/applications ~/.local/share/icons/hicolor/scalable/apps
cp data/br.com.vigia.SelinuxGui.desktop ~/.local/share/applications/
cp data/br.com.vigia.SelinuxGui.svg ~/.local/share/icons/hicolor/scalable/apps/
gtk-update-icon-cache ~/.local/share/icons/hicolor 2>/dev/null || true
update-desktop-database ~/.local/share/applications 2>/dev/null || true
```

Ou abre via **Vigia Hub** (apartir da v0.2 do Hub registra esta ferramenta).

## Limitações v0.1

- **Mudança de modo (Enforcing↔Permissive) é apenas runtime** — não persiste no
  reboot. Persistência requer editar `/etc/selinux/config` + reboot. v0.2
  vai oferecer essa opção como switch separado.
- **Sem AVC denials tab** — use o Vigia Activity Log para isso (filtre por AVC
  no header com `f`).
- **Sem file contexts** — `semanage fcontext` adiciona complexidade significativa,
  fica para v0.3.
- **Cada toggle pede senha** (pkexec sem cache). v0.3 vai usar D-Bus service
  com polkit policy `auth_admin_keep`.

## Roadmap

- **v0.2**: toggle "Enforcing persistente" (edita `/etc/selinux/config`),
  status mode detalhado (Process / File / etc.)
- **v0.3**: D-Bus helper para cache polkit, tab de AVC denials com integração
  ao Activity Log
- **v0.4**: file contexts (visualizar + adicionar regras via semanage fcontext)
- **v0.5**: `audit2allow` integrado — quando uma denial aparece, oferece "sugerir
  módulo de policy customizada"
