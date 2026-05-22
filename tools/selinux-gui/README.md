# Vigia SELinux GUI

> Gerenciador moderno em GTK4 + libadwaita para SELinux. Substituto visual do
> `system-config-selinux` (que ainda é GTK2).

## Estado

🟢 **v0.2** — 6 tabs cobrindo a maior parte da administração SELinux:

### Status
- Modo runtime (Enforcing / Permissive / Disabled) com cor semântica
- **Modo persistente** (lê `/etc/selinux/config`) — dropdown para mudar
- Política ativa (`targeted` etc.) + versão
- Switch Enforcing/Permissive runtime via `pkexec setenforce`
- Combo persistent mode edita `/etc/selinux/config` via `pkexec sed`

### Booleans
- Lista completa (~300 entries em Fedora)
- **Descrições em pt-BR** (dict hardcoded para top ~60 + fallback `semanage boolean -l`)
- Search bar filtra por **nome OU descrição** (ex: "anônimo", "rede", "ssh")
- Switch persistente via `pkexec setsebool -P`

### Denials (AVC)
- Lista de bloqueios SELinux recentes via `pkexec ausearch -m AVC`
- Filtro por período (Hoje / Esta semana / Recente / Este mês)
- Cada denial mostra: processo, pid, operação, path, scontext→tcontext, BLOQUEADO vs permissive
- Botão "Gerar" para `audit2allow` — produz módulo de policy customizada que permitiria a operação
- Linha raw expandível para copiar/inspecionar

### Files
- Input para path + opções (-R recursivo, -v verbose)
- Botão "Restaurar contextos" → `pkexec restorecon`
- Saída do comando em viewer monospace

### Network
- Lista de port mappings SELinux (`semanage port -l`)
- Search/filter por contexto/porta/protocolo
- Read-only em v0.2 (adicionar/remover ports em v0.3)

### Processes
- Contextos SELinux dos processos rodando (`ps -eZ`)
- Search/filter por comm, user ou contexto
- Read-only (informativo/educacional)

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

## Limitações v0.2

- **Cada operação pede senha** (pkexec sem cache). v0.3 vai usar D-Bus service
  com polkit policy `auth_admin_keep` (cache ~5min).
- **Network ports é read-only** — adicionar/remover via `semanage port -a/-d` em v0.3.
- **File contexts (semanage fcontext)** — apenas restorecon disponível. Adicionar
  regras de label customizadas em v0.3.
- **audit2allow gera o texto mas não compila/instala** o módulo automaticamente.
  Você precisa rodar `checkmodule`/`semodule_package`/`semodule -i` manualmente.
- **Descrições pt-BR cobrem ~60 booleans** dos ~300 totais. PRs com mais
  traduções são bem-vindas (edite `descriptions.py`).

## Roadmap

- ✅ **v0.1**: Status + Booleans básicos
- ✅ **v0.2**: 6 tabs (Status com persistent mode, Booleans com descrições,
  Denials com audit2allow, Files com restorecon, Network ports read-only, Processes)
- **v0.3**: D-Bus helper + polkit policy (cache de auth), adicionar/remover ports,
  file contexts customizados, compilar+instalar policy do audit2allow com um botão
- **v0.4**: módulos custom (load/unload .pp files), login mappings, user contexts
- **v0.5**: integração com Activity Log (clique em denial lá → abre Denials aqui)
