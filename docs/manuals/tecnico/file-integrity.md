# File Integrity

## Em uma frase

Wrapper GTK4 para `aide` (intrusion detection sistema-wide com baseline
SHA256 + diff) combinado com hash ad-hoc (`hashlib`) para arquivos do
usuário — duas escalas, mesma lógica de "baseline + diff".

## O que envolve

| Item | Valor |
|---|---|
| **Pacote** | `vigia-file-integrity` (versão 0.2.0) |
| **App ID** | `br.com.vigia.FileIntegrity` |
| **Pacotes wrapped** | `aide`, `coreutils` (hashlib do Python stdlib para hash ad-hoc) |
| **Privilégios** | AIDE: tudo via `pkexec`. Hash ad-hoc: sem privilégios |
| **Path config (sistema)** | `/etc/aide.conf` + `/var/lib/aide/aide.db.gz` |
| **Path config (Silverblue)** | `/etc/aide-vigia.conf` + `/var/lib/aide/aide.db.vigia.gz` |
| **State local** | `~/.config/vigia/file-integrity.json` (0600) + `~/.local/share/vigia-hash/` (0700) |
| **Stack** | Python 3.11+ . PyGObject . GTK4 . libadwaita 1 |

## Arquitetura interna

```
vigia_integrity/
|-- backend.py          # AIDE: init/check/update + parse_check_output + perfis
|-- hash_backend.py     # hashlib/hashdeep: hash, verify, create/compare baseline (detecta movido)
|-- window.py           # build_content() — 6 tabs no Adw.ViewStack
`-- tabs/
    |-- status.py       # Hero + acoes Criar/Verificar/Atualizar baseline
    |-- changes.py      # diff do ultimo aide --check (added/removed/changed)
    |-- hash_tab.py     # calcula hash de 1 arquivo (sha256/512/sha1/md5)
    |-- verify.py       # compara hash esperado vs computado
    |-- baseline.py     # snapshot de diretorio em JSON + diff added/removido/modificado/movido (sem root)
    `-- about.py
```

### Dois perfis AIDE

| Perfil | Config | DB | Quando usar |
|---|---|---|---|
| **Sistema padrão** | `/etc/aide.conf` | `aide.db.gz` | Distros tradicionais. Em Silverblue, monitora `/usr` que muda a cada upgrade -> ruído massivo. |
| **Silverblue (Vigia)** | `/etc/aide-vigia.conf` | `aide.db.vigia.gz` | Exclui `/usr`, `/boot`, `/ostree`, `/sysroot` (cobertos pelo OSTree criptográfico). Foca em `/etc`, `/root`, `/var/spool/cron`, `/usr/local`. |

`silverblue_profile_active()` -> True se `/etc/aide-vigia.conf` existe.
`active_conf_path()` / `active_db_path()` / `active_db_new_path()`
resolvem o perfil automaticamente.

### Cache LGPD em STATE_FILE

`/var/lib/aide/` é 0700 (root-only). `baseline_exists()` evita
`stat()` no path (vazaria info para outros users em sistema
multi-user). Usa proxy em `~/.config/vigia/file-integrity.json`:

```json
{"baseline_exists": true, "baseline_mtime": 1716894000, "last_check": {...}}
```

Atualizado em `run_init_blocking()` e `run_update_blocking()`.

## Comandos disparados

```bash
# Criar baseline (sistema vazio)
pkexec bash -c '
set -e
rm -f /var/lib/aide/aide.db.vigia.new.gz
aide -c /etc/aide-vigia.conf --init
mv -f /var/lib/aide/aide.db.vigia.new.gz /var/lib/aide/aide.db.vigia.gz
'

# Verificar
pkexec aide -c /etc/aide-vigia.conf --check
# Returncode: 0 = sem mudancas; 1-7 = bitmask added/removed/changed; 8+ = erro

# Atualizar baseline (apos aplicar mudancas legitimas)
pkexec bash -c '
aide -c /etc/aide-vigia.conf --update
mv -f /var/lib/aide/aide.db.vigia.new.gz /var/lib/aide/aide.db.vigia.gz
'

# Aplicar perfil Silverblue (escreve /etc/aide-vigia.conf via heredoc)
pkexec bash -c 'cat > /etc/aide-vigia.conf << EOF ... EOF; chmod 644'

# Remover perfil Silverblue
pkexec bash -c '
rm -f /etc/aide-vigia.conf
rm -f /var/lib/aide/aide.db.vigia.gz
rm -f /var/lib/aide/aide.db.vigia.new.gz
'

# Hash ad-hoc (Python stdlib, sem subprocess)
hashlib.new("sha256").update(chunk)  # 1MB por iteracao
```

## Tabs / Funcionalidades

| Tab | Escala | Privilégios | Descrição |
|---|---|---|---|
| **Status (AIDE)** | Sistema | root | Hero card mostrando estado + ações "Criar baseline" / "Verificar agora" / "Atualizar baseline". Controle de perfil (Aplicar/Remover Silverblue). Stats do último check. |
| **Mudanças (AIDE)** | Sistema | root | Lista added/removed/changed do último `aide --check`. Para changed mostra quais propriedades mudaram (perms, mtime, size, sha256...). |
| **Hash** | Arquivo único | user | File picker + ComboRow algoritmo (sha256/sha512/sha1/md5) + botão Calcular + copy hash. |
| **Verificar** | Arquivo único | user | Hash esperado + arquivo + algoritmo -> matches/computed. Aceita format `sha256sum` (`<hash>  <filename>`). |
| **Baseline** | Diretório | user | Cria JSON de hashes recursivos em `~/.local/share/vigia-hash/baseline-<dir>-<ts>.json`. Comparar baseline diz added/removed/modified/unchanged. |
| **Sobre** | — | — | Explica AIDE + perfil Silverblue + paths monitorados (extraídos via `parse_conf_watched_paths()`). |

## Quando usar

- **Pós-instalação do sistema**: criar baseline AIDE (perfil Silverblue
  recomendado para Fedora atômicas).
- **Pós-rpm-ostree upgrade**: rodar `aide --check`, validar mudanças
  legítimas em `/etc`, clicar "Re-baseline" para aceitar.
- **Forense / cadeia de custódia**: tab Hash + Verificar com sha256/sha512.
- **Snapshot de diretório user-space**: tab Baseline para `/home/andre/casos/processo-X`.

## Limitações conhecidas

- AIDE check em sistema completo demora minutos (timeout 30min default).
- Cache de status no `STATE_FILE` pode ficar dessincronizado se baseline
  for criada via terminal direto (`pkexec aide --init` fora da tool).
- Baseline ad-hoc segue symlinks? Não — pula com
  `if not f.is_file() or f.is_symlink(): continue`.
- Hash ad-hoc rejeita device/fifo/socket files (evita loop infinito de
  I/O em `/dev/zero`).

## Trecho de código relevante

Perfil Silverblue otimizado (`backend.py:558`):

```
NORMAL = R+sha256
/etc NORMAL                         # config, sudoers, passwd, shadow
/root NORMAL                        # .ssh, dotfiles
/var/spool/cron NORMAL              # cron jobs (vetor classico)
/usr/local NORMAL                   # instalacoes fora do OSTree

# Exclusoes — cobertos pelo OSTree criptografico
!/usr/bin
!/usr/sbin
!/usr/lib
!/ostree
!/boot
```

Hash chunked com 1MB (`hash_backend.py:113`):

```python
h = hashlib.new(algorithm)
with open(p, "rb") as f:
    while True:
        chunk = f.read(1 << 20)  # 1 MB
        if not chunk:
            break
        h.update(chunk)
return h.hexdigest(), ""
```

Parser do output AIDE (`backend.py:262`) usa regex
`^[fld][^:]*?:\s+(/.*)$` para extrair path (versões anteriores faziam
`rsplit(":", 1)` que falhava silenciosamente em paths com `:`).
