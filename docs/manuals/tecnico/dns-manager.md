# DNS Manager

## Em uma frase

Wrapper para `dnscrypt-proxy` com catálogo curado de 11 servers
(DoH/DoT/DNSCrypt), edição linha-a-linha do `/etc/dnscrypt-proxy.toml`
preservando comentários, e migração 1-click de `systemd-resolved` para
`dnscrypt-proxy` como backend DNS do sistema.

## O que envolve

| Item | Valor |
|---|---|
| **Pacote** | `vigia-dns-manager` (versão 0.4.1) |
| **App ID** | `br.com.vigia.DnsManager` |
| **Pacotes wrapped** | `dnscrypt-proxy` |
| **Privilégios** | `pkexec systemctl` + `pkexec bash -c` (escrita atômica de config) |
| **Path config** | `/etc/dnscrypt-proxy/dnscrypt-proxy.toml` |
| **Backup config** | `.vigia-backup` (chmod 0600) |
| **Backup resolved** | `/etc/systemd/resolved.conf.vigia-resolved-backup` |
| **Stack** | Python 3.11+ . PyGObject . GTK4 . libadwaita 1 |

## Arquitetura interna

```
vigia_dns/
|-- dnscrypt_backend.py    # get_status + set_servers + enable/disable + parse TOML
|-- dnscrypt_catalog.py    # 11 DnsCryptServer curados
|-- migration.py           # ensure_dnscrypt_active + restore_systemd_resolved
|-- window.py              # 3 tabs no Adw.ViewStack
`-- tabs/
    |-- status.py          # hero estado + acoes Ativar/Restaurar
    |-- resolvers.py       # catalogo + botao Aplicar
    `-- about.py
```

> Nota histórica: o código em `tabs/about.py` ainda fala de "Modo
> simples (systemd-resolved DoT)" vs "Modo avançado (dnscrypt-proxy)" —
> texto stale da v0.2. Desde v0.3 a tool é **dnscrypt-only**. A v0.4
> removeu blocklists e stats (ad-blocking é melhor servido por uBlock
> Origin via Tool Installer).

### Catálogo de 11 servers

| Provider | Servers | País |
|---|---|---|
| **Cloudflare** | `cloudflare` (DoH), `cloudflare-security` (1.1.1.2 malware), `cloudflare-family` (1.1.1.3 adult) | US |
| **Quad9** | `quad9-doh-ip4-port443-filter-pri` (9.9.9.9 filtrado), `quad9-doh-ip4-nofilter-pri` (9.9.9.10) | CH |
| **AdGuard** | `adguard-dns-doh`, `adguard-dns-family-doh` | CY |
| **Mullvad** | `mullvad-doh`, `mullvad-adblock-doh` | SE |
| **DNSCrypt nativo** | `dnscrypt-quad9` (alternativa a HTTPS) | CH |
| **Anonymized** | `anon-cs-fr` (relay FR — esconde IP do user do resolver) | FR |

`default_servers()` retorna `["cloudflare", "quad9-doh-ip4-port443-filter-pri"]`.
Cada server tem flags `no_logs`, `no_filter`, `dnssec`.

### Migração systemd-resolved -> dnscrypt-proxy

`migration.ensure_dnscrypt_active_blocking()` consolida 5 passos em UM
`pkexec`:

1. Backup `/etc/systemd/resolved.conf` -> `.vigia-resolved-backup` (chmod 0600)
2. Backup `/etc/resolv.conf` -> `.vigia-resolved-backup`
3. `systemctl stop systemd-resolved && systemctl disable systemd-resolved`
4. Reescreve `/etc/resolv.conf` com `nameserver 127.0.0.1 / nameserver ::1 / options edns0`
5. `systemctl enable --now dnscrypt-proxy`

`dnscrypt_active_ready()` valida: dnscrypt ativo E `/etc/resolv.conf`
aponta para `127.0.0.1` ou `::1`. Detecta symlink para
`stub-resolv.conf` (systemd) como NOT ready.

### Edição TOML preservando comentários

`_read_config_lines()` lê como `list[str]`. `_update_toml_key(lines,
key, new_value)` faz regex `^(\s*){key}\s*=` no scope global (sem
section). Se não acha, insere antes da primeira `[...]`. Preserva
indentação e comentários.

Validação anti-injection em `set_servers_blocking`: nomes devem casar
`^[a-zA-Z0-9._\-]+$` — caso contrário rejeita.

### Cache dir warning fix (v0.4.1)

`_atomic_write_config_via_pkexec` detecta `User`/`Group` do unit file
dinamicamente e garante `/var/cache/dnscrypt-proxy/` 0750:

```bash
DCS_USER=$(systemctl show dnscrypt-proxy -p User --value)
DCS_GROUP=$(systemctl show dnscrypt-proxy -p Group --value)
mkdir -p /var/cache/dnscrypt-proxy
chown "${DCS_USER}:${DCS_GROUP:-$DCS_USER}" /var/cache/dnscrypt-proxy
chmod 0750 /var/cache/dnscrypt-proxy
```

## Comandos disparados

```bash
# Sanity
systemctl is-active --quiet dnscrypt-proxy
systemctl is-enabled --quiet dnscrypt-proxy
dnscrypt-proxy -version

# Ativar (primeira vez ou apos restore)
pkexec bash -c '
set -e
cp -a /etc/systemd/resolved.conf /etc/systemd/resolved.conf.vigia-resolved-backup
chmod 0600 /etc/systemd/resolved.conf.vigia-resolved-backup
cp -aP /etc/resolv.conf /etc/resolv.conf.vigia-resolved-backup
systemctl stop systemd-resolved
systemctl disable systemd-resolved
mkdir -p /var/cache/dnscrypt-proxy
chmod 0750 /var/cache/dnscrypt-proxy
rm -f /etc/resolv.conf
cat > /etc/resolv.conf << EOF
nameserver 127.0.0.1
nameserver ::1
options edns0
EOF
systemctl enable --now dnscrypt-proxy
'

# Trocar servers (editar TOML + restart)
pkexec bash -c '
set -e
cp -a /etc/dnscrypt-proxy/dnscrypt-proxy.toml /etc/dnscrypt-proxy/dnscrypt-proxy.toml.vigia-backup
TMPFILE=$(mktemp)
cat > "$TMPFILE" << EOF
<novo conteudo>
EOF
mv "$TMPFILE" /etc/dnscrypt-proxy/dnscrypt-proxy.toml
systemctl restart dnscrypt-proxy
'

# Voltar atras (uninstall path)
pkexec bash -c '
systemctl stop dnscrypt-proxy
systemctl disable dnscrypt-proxy
cp -a /etc/systemd/resolved.conf.vigia-resolved-backup /etc/systemd/resolved.conf
cp -aP /etc/resolv.conf.vigia-resolved-backup /etc/resolv.conf
systemctl enable --now systemd-resolved
'
```

## Tabs / Funcionalidades

| Tab | Descrição |
|---|---|
| **Status** | Hero com 4 estados: "não instalado" / "parado" / "Quase lá" (rodando mas resolv.conf não aponta) / "Ativo e seguro". Action bar: Atualizar / Ativar dnscrypt-proxy / Restaurar systemd-resolved. Info group: serviço/versão/listen address. Config group: servers ativos, require DNSSEC, require no-logs. |
| **Provedores** | Lista os 11 servers em `Adw.ExpanderRow` com badges (DoH/DoT/DNSCrypt, no-logs, DNSSEC, no-filter, country). Aplicar -> `set_servers_blocking([id])` -> edita TOML -> restart dnscrypt-proxy. Banner amarelo se dnscrypt não está ativo. |
| **Sobre** | 5 seções markup-formatted (NB: parte do texto é v0.2 stale). |

## Quando usar

- **Setup novo de privacidade**: instalar dnscrypt-proxy via Tool
  Installer + Ativar pelo DNS Manager + escolher Cloudflare + Quad9.
- **LGPD/escritório**: AdGuard ou Mullvad AdBlock para bloquear
  tracking corporate no nível DNS.
- **Forçar DNSSEC explícito**: garantir que respostas DNS não foram
  manipuladas no caminho.
- **Voltar atrás**: "Restaurar systemd-resolved" se outra tool exigir
  o default Fedora.

## Limitações conhecidas

- Requer `dnscrypt-proxy` instalado (via `dnf` ou Tool Installer). Hero
  mostra "não instalado" se ausente.
- Editar `/etc/dnscrypt-proxy/dnscrypt-proxy.toml` direto durante uso
  da tool pode causar diff em key insertion (Vigia usa regex line-based,
  não re-serializa o TOML inteiro).
- NetworkManager pode reescrever `/etc/resolv.conf` em reconexão se
  config da conexão não tem `ignore-auto-dns yes`.
- Anonymized DNS Relay (`anon-cs-fr`) listado mas requer setup
  adicional de `anonymized_dns` no .toml (v0.2.1+).
- Texto da aba "Sobre" é stale (fala de Modo simples / Modo avançado da v0.2).

## Trecho de código relevante

Idempotência em ensure_dnscrypt (`migration.py:103`):

```python
def ensure_dnscrypt_active_blocking() -> tuple[bool, str]:
    if dnscrypt_active_ready():
        return True, ""  # ja esta ativo, no-op
    # ... script pkexec ...
```

Edição TOML preservando comentários (`dnscrypt_backend.py:188`):

```python
def _update_toml_key(lines: list[str], key: str, new_value: str) -> list[str]:
    pattern = re.compile(rf"^(\s*){re.escape(key)}\s*=", re.MULTILINE)
    out: list[str] = []
    replaced = False
    in_section = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_section = True
        if not in_section and pattern.match(line):
            indent = pattern.match(line).group(1)
            out.append(f"{indent}{key} = {new_value}\n")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        # insere antes da primeira [section]
        ...
    return out
```

Validação anti-injection (`dnscrypt_backend.py:326`):

```python
def set_servers_blocking(server_names: list[str]) -> tuple[bool, str]:
    for name in server_names:
        if not re.match(r"^[a-zA-Z0-9._\-]+$", name):
            return False, f"Nome de server invalido: {name!r}"
    array_repr = "[" + ", ".join(f"'{s}'" for s in safe) + "]"
    new_lines = _update_toml_key(lines, "server_names", array_repr)
    return _atomic_write_config_via_pkexec("".join(new_lines))
```
