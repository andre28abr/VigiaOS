# Tool Installer

## Em uma frase

Catálogo curado de 13 ferramentas de segurança instaláveis com 1 clique
via `dnf` + catálogo de 8 extensões FOSS para navegadores que
abrem em AMO/Chrome Web Store via `xdg-open`.

## O que envolve

| Item | Valor |
|---|---|
| **Pacote** | `vigia-tool-installer` (versão 0.4.0) |
| **App ID** | `br.com.vigia.ToolInstaller` |
| **Pacotes wrapped** | `dnf`, `rpm`, `xdg-open` |
| **Privilégios** | `pkexec dnf install/remove/upgrade` (checagem via `rpm -q`, sem root) |
| **State local** | `~/.config/vigia-installer/browser-extensions.json` |
| **Stack** | Python 3.11+ . PyGObject . GTK4 . libadwaita 1 |

## Arquitetura interna

```
vigia_installer/
|-- backend.py             # dnf install/remove/upgrade + rpm -q + check_updates
|-- catalog.py             # CATALOG: 13 CatalogEntry em 5 categorias
|-- browser_extensions.py  # detect_installed_browsers + CATALOG extensoes + state
|-- window.py              # 4 tabs no Adw.ViewStack
`-- tabs/
    |-- browse.py          # catalogo categorizado + search + install/remove
    |-- updates.py         # checa/aplica updates do sistema (dnf)
    |-- extensions.py      # extensoes por navegador detectado
    `-- about.py
```

### Catálogo de pacotes (5 categorias)

| Categoria | Pacotes |
|---|---|
| **Auditoria e hardening** | lynis, aide, chkrootkit, rkhunter |
| **Rede** | mtr, nethogs |
| **Monitoramento e diagnóstico** | lsof, strace, fail2ban |
| **Privacidade e criptografia** | NetworkManager-openvpn-gnome, dnscrypt-proxy |
| **Forense e análise** | clamav, hashdeep |

Cada `CatalogEntry` tem `package`, `name`, `description` (1 linha),
`why` (parágrafo com markdown leve via `_md_to_pango`), `category`,
`binary` (para detecção). `by_category()` retorna agrupado preservando
ordem em `CATEGORIES_ORDER`.

### Catálogo de extensões (8 FOSS)

| Extensão | Categoria | License | Firefox slug / Chrome ID |
|---|---|---|---|
| uBlock Origin | ad-blocker | GPL-3.0 | `ublock-origin` / `cjpalhdlnbpafiamejdnhcphjbkeiagm` |
| AdGuard AdBlocker | ad-blocker | GPL-3.0 | `adguard-adblocker` / `bgnkhhnnamicmpeenaelnjfhikgbkllg` |
| Privacy Badger | tracker-blocker | GPL-3.0 | `privacy-badger17` / `pkehgijcmpdhfbdbbnkijodmdjhbjlgp` |
| ClearURLs | url-cleaner | LGPL-3.0 | `clearurls` / `lckanjgmijmafbedllaakclkaicjfmnk` |
| LibRedirect | redirector | GPL-3.0 | `libredirect` / (só Firefox) |
| Cookie AutoDelete | cookie-manager | MIT | `cookie-autodelete` / `fhcgjolkccmbidfldomjliifgaodjagh` |
| Decentraleyes | cdn-cache | MPL-2.0 | `decentraleyes` / (só Firefox) |

Categoria `ad-blocker` está em `EXCLUSIVE_CATEGORIES` — `find_conflicts()`
detecta se user já marcou uBlock e está tentando marcar AdGuard, dispara
dialog "Substituir uBlock?".

### Navegadores suportados

`detect_installed_browsers()` usa `shutil.which(binary)` para cada:
firefox, firefox-esr, librewolf, google-chrome, chromium-browser,
brave-browser, vivaldi. Família firefox/chromium determina qual URL
gerar (AMO vs Chrome Web Store).

### Status de instalação via `rpm -q`

```python
def is_package_installed(pkg: str) -> bool:
    # rpm -q <pkg>  -> returncode 0 = instalado (sem root)
    result = subprocess.run(["rpm", "-q", pkg], capture_output=True,
                            text=True, timeout=5)
    return result.returncode == 0
```

O `dnf install` aplica na hora; não há conceito de "mudanças staged /
reboot pendente". O status é binário: **Disponível** ou **INSTALADO**.

### Checagem e aplicação de atualizações (aba Atualizações)

```python
def check_updates() -> UpdateInfo:
    # dnf check-update  (rc 100 = update, 0 = nada, outro = erro)
    # parse_dnf_check_update extrai os nomes dos pacotes

def update_command(elevated=False) -> list[str]:
    # ["dnf","upgrade","-y"]; elevated=True prefixa "pkexec"
    # (uso no painel do Hub)
```

`check_updates()` é **read-only** (sem root) e roda em worker thread ao
abrir a aba (notificação no próprio painel). `run_system_update_blocking()`
aplica via `pkexec` (timeout 1800s). O comando "puro"
(`update_command_display()` → `sudo dnf upgrade`) é
exposto **copiável** pro usuário rodar no terminal — os dois caminhos
coexistem (painel vs terminal, o usuário escolhe).

## Comandos disparados

```bash
# Verificar instalacao (read-only, sem root)
rpm -q lynis                         # returncode 0 = instalado

# Instalar (aplica na hora, sem reboot)
pkexec dnf install -y lynis aide chkrootkit

# Desinstalar
pkexec dnf remove -y lynis

# Checar atualizacoes (read-only, sem root)
dnf check-update                # rc 100 = update, 0 = nada

# Aplicar atualizacao do sistema (caminho "painel", aplica na hora)
pkexec dnf upgrade -y

# Extensao: abrir URL no navegador default
xdg-open "https://addons.mozilla.org/firefox/addon/ublock-origin/"
xdg-open "https://chromewebstore.google.com/detail/cjpalhdlnbpafiamejdnhcphjbkeiagm"
```

## Tabs / Funcionalidades

| Tab | Descrição |
|---|---|
| **Catálogo** | Lista categorizada em `Adw.PreferencesGroup`. Cada item é `Adw.ExpanderRow` com prefix badge de status (`Disponivel` / `INSTALADO`) + suffix botão ação (`Instalar` / `Remover`). Expansão mostra `why` + nome do pacote. Status carregado em worker thread (`refresh_statuses_async`). Search filtra em nome/desc/pacote/why. |
| **Atualizações** | Checagem automática ao abrir (worker thread → hero "N atualizações" / "Sistema atualizado"). Dois caminhos: botão `Atualizar agora` (`pkexec dnf upgrade -y`, aplica na hora) e comando copiável pro terminal (`update_command_display`). Lista **separada por origem**: **Sistema** vs **Programas da suíte Vigia** (`split_updates` + `catalog.is_suite_package`). |
| **Extensões** | Detecta navegadores instalados, lista catálogo FOSS + botão "Abrir no <browser>" (xdg-open URL da AMO/Web Store). Marcação manual de "já instalei" persistente em JSON. Lock por categoria ad-blocker (só 1 por browser). |
| **Sobre** | 5 seções markup-formatted. |

## Quando usar

- **Setup pós-instalação**: instalar lynis + aide + chkrootkit em
  sequência (aplica na hora, sem reboot).
- **Hardening incremental**: adicionar fail2ban quando começar a expor
  serviço SSH.
- **Privacidade browser**: instalar uBlock Origin + Privacy Badger +
  ClearURLs em Firefox novo.
- **Forense**: clamav + hashdeep para investigar máquina comprometida.

## Limitações conhecidas

- Sem multi-select (v0.2 roadmap: checkboxes + 1 transação para vários
  pacotes simultâneos).
- Sem busca em repos externos — apenas o catálogo curado.
- Instalações com muitas dependências podem demorar 5-10min.
- Extensões não tem detecção real de "instalada no browser" — apenas
  marcação manual em JSON local. CLI APIs do browser não permitem instalar.
- `dnscrypt-proxy` no catálogo mas o DNS Manager v0.4 já gerencia ele
  nativamente; instalar via Tool Installer é redundante se já usa o DNS Manager.

## Trecho de código relevante

Install consolidado (`backend.py`):

```python
def install_packages_blocking(packages: list[str]) -> tuple[bool, str]:
    cmd = ["pkexec", "dnf", "install", "-y"] + list(packages)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if result.returncode in (126, 127):
        return False, "Autenticacao cancelada."
    if result.returncode != 0:
        return False, f"Falha (codigo {result.returncode}):\n\n{out[:800]}"
    return True, result.stdout.strip()
```

Conflict detection em categorias exclusivas
(`browser_extensions.py:302`):

```python
def find_conflicts(ext_id: str, browser_id: str) -> list[str]:
    ext = find_extension(ext_id)
    if ext is None or ext.category not in EXCLUSIVE_CATEGORIES:
        return []
    installed_map = _load_state().get("installed", {})
    conflicts = []
    for other_id, browsers in installed_map.items():
        if other_id == ext_id or browser_id not in browsers:
            continue
        other = find_extension(other_id)
        if other and other.category == ext.category:
            conflicts.append(other_id)
    return conflicts
```
