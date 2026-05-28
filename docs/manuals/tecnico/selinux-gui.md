# SELinux Manager (selinux-gui)

## Em uma frase

Wrapper GTK4 para `semanage`, `setsebool`, `audit2allow` e `restorecon` —
substitui o antigo `system-config-selinux` (GTK2) com 6 tabs cobrindo
status, booleans, denials AVC, restore de contextos, port mappings e
contextos de processos.

## O que envolve

| Item | Valor |
|---|---|
| **Pacotes Linux** | `selinux-policy-targeted`, `policycoreutils`, `policycoreutils-python-utils` (audit2allow + semanage), `audit` (ausearch) |
| **Comando principal** | `getenforce`, `getsebool -a`, `semanage boolean -l`, `pkexec setsebool -P`, `pkexec ausearch -m AVC`, `pkexec restorecon -R -v` |
| **Permissões** | Read-only roda como user. Write ops via `pkexec` (Polkit) |
| **Stack** | Python 3.11+ · PyGObject · GTK4 · libadwaita 1 |
| **Path config** | Sem state local — lê `/etc/selinux/config` e `/var/log/audit/audit.log` |
| **App ID** | `br.com.vigia.SelinuxGui` |
| **Versão** | 0.2.0 |

## Arquitetura interna

```
vigia_selinux/
├── backend.py       — subprocess wrappers (getenforce, semanage, setsebool, ausearch...)
├── descriptions.py  — dict de descrições pt-BR de ~50 booleans comuns
├── window.py        — build_content() monta ViewStack das 6 tabs
└── tabs/
    ├── status.py    — modo runtime + persistente + info de policy
    ├── booleans.py  — lista pesquisável + toggles (Switch por row)
    ├── denials.py   — AVC blocks recentes + audit2allow
    ├── files.py     — restorecon (recursive, verbose)
    ├── network.py   — port mappings (read-only)
    └── processes.py — contextos SELinux de processos rodando
```

Cada operação que pode demorar (semanage, setsebool -P, ausearch,
restorecon) roda em `threading.Thread(daemon=True)` e finaliza via
`GLib.idle_add` no UI thread — UI nunca trava.

## Comandos disparados

```bash
# Status (user, sem auth)
getenforce
sestatus
cat /etc/selinux/config        # lê SELINUX=

# Booleans
semanage boolean -l            # com descrição upstream
getsebool -a                   # fallback se semanage falhar

# Mudar boolean (root)
pkexec setsebool -P httpd_can_network_connect on

# Mudar modo runtime
pkexec setenforce 0|1

# Mudar modo persistente (edita /etc/selinux/config)
pkexec sh -c "sed -i 's/^SELINUX=.*/SELINUX=enforcing/' /etc/selinux/config"

# AVC denials
pkexec ausearch -m AVC -ts today --raw

# Gerar policy custom
audit2allow                    # recebe linha raw via stdin

# Restaurar contextos
pkexec restorecon -R -v -- /var/www

# Port mappings
semanage port -l

# Contextos de processos
ps -eZ -o label,pid,user,comm --no-headers
```

## Tabs / Funcionalidades

### Status

Mostra **modo runtime** (`getenforce`), **modo persistente** (linha
`SELINUX=` em `/etc/selinux/config`), tipo de política (`targeted`
normalmente) e versão. Switch troca modo runtime via `setenforce 0|1`.
ComboRow troca modo persistente reescrevendo `/etc/selinux/config` via
`pkexec sh -c "sed -i ..."`.

### Booleans

Lista filtrável de ~300 SELinux booleans. Cada row tem switch.
Descrições pt-BR vêm de `descriptions.py` (curadas para os ~50 mais
comuns) com fallback para a descrição upstream do `semanage`. Toggle
roda `pkexec setsebool -P` (persistente) em thread — pode demorar
vários segundos porque recompila a policy.

### Denials

ComboRow de período (`today`, `this-week`, `recent`, `this-month`).
Botão "Carregar denials" dispara `pkexec ausearch -m AVC -ts <since>
--raw`. Parser regex extrai `comm`, `pid`, op (`{ write }`), `scontext`,
`tcontext`, `tclass` e flag `permissive`. Cada denial vira ExpanderRow
com linha raw + botão "Gerar" que roda `audit2allow` via stdin e abre
AlertDialog com a sugestão de policy + instruções de `checkmodule` +
`semodule_package` + `semodule -i`.

### Files

Form com path + switches recursive/verbose. Botão executa `pkexec
restorecon -R -v -- <path>` em thread (timeout 120s). Output do comando
aparece num TextView monospace. O `--` antes do path evita interpretação
de paths que começam com `-` como flag.

### Network

`semanage port -l` parseado em rows (contexto, proto, ports). Read-only
nesta versão — edição via `semanage port -a` virá em v0.3.

### Processes

`ps -eZ -o label,pid,user,comm` listado e filtrável. Mostra só o tipo
SELinux (parte 3 do contexto `system_u:object_r:httpd_t:s0` → `httpd_t`)
no subtitle.

## Quando usar

- Serviço parou de funcionar após mudança de configuração — aba
  **Denials** revela se foi SELinux + sugere fix
- Habilitar boolean conhecido para um caso (Apache acessar rede, NFS
  compartilhar home, etc.) — aba **Booleans**
- Movi arquivos manualmente e o app que usa esses arquivos falhou — aba
  **Files** com restorecon resolve 90% dos casos
- Auditar quais processos rodam em quais domínios SELinux — aba
  **Processes**

## Limitações conhecidas

- Toggle de boolean persistente recompila a policy SELinux — pode levar
  3-10s por toggle. UI mostra spinner mas é a realidade do `setsebool -P`.
- `restorecon` recursivo em árvores grandes (ex: `/home`) pode levar
  minutos. Timeout default é 120s — se exceder, levanta exception.
- Network tab é read-only — `semanage port -a/-d` ainda não tem GUI.
- Audit2allow gera o `.te`, mas o usuário ainda precisa rodar
  `checkmodule` + `semodule_package` + `semodule -i` manualmente.
- Não há integração com `setroubleshoot`/`sealert` — só `ausearch`
  direto.

## Trecho de código relevante

```python
# backend.py — restorecon com guard contra path-as-flag
def restorecon(path: str, recursive: bool = True, verbose: bool = True) -> str:
    _require_pkexec()
    args = ["pkexec", "restorecon"]
    if recursive:
        args.append("-R")
    if verbose:
        args.append("-v")
    # '--' separa flags de argumentos posicionais. Sem isso, path tipo
    # '--help' ou '-F' seria interpretado como flag pelo restorecon.
    args.append("--")
    args.append(path)
    result = subprocess.run(args, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout).strip()
        if "Request dismissed" in stderr or result.returncode == 126:
            raise RuntimeError("Autenticacao cancelada pelo usuario.")
        raise RuntimeError(f"restorecon falhou: {stderr}")
    return result.stdout.strip() or "Nenhuma label precisava ser restaurada."
```

```python
# backend.py — parser de AVC denials (regex sobre output --raw do ausearch)
def _parse_ausearch_avc(output: str) -> list[Denial]:
    denials: list[Denial] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line.startswith("type=AVC"):
            continue
        ts_match = re.search(r"msg=audit\(([\d.]+):\d+\)", line)
        op_match = re.search(r"\{\s*(\S+)\s*\}", line)
        perm_match = re.search(r"permissive=(\d)", line)
        fields = dict(re.findall(r'(\w+)="?([^"\s]+)"?', line))
        denials.append(Denial(...))
    return denials
```
