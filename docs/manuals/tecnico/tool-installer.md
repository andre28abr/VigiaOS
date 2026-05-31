# Tool Installer

## Em uma frase

Catálogo curado de 16 ferramentas de segurança instaláveis com 1 clique
via `rpm-ostree` + catálogo de 8 extensões FOSS para navegadores que
abrem em AMO/Chrome Web Store via `xdg-open`.

## O que envolve

| Item | Valor |
|---|---|
| **Pacote** | `vigia-tool-installer` (versão 0.2.0) |
| **App ID** | `br.com.vigia.ToolInstaller` |
| **Pacotes wrapped** | `rpm-ostree`, `xdg-open` |
| **Privilégios** | `pkexec rpm-ostree install/uninstall` |
| **State local** | `~/.config/vigia-installer/browser-extensions.json` |
| **Stack** | Python 3.11+ . PyGObject . GTK4 . libadwaita 1 |

## Arquitetura interna

```
vigia_installer/
|-- backend.py             # rpm-ostree install/uninstall/status/pending_changes
|-- catalog.py             # CATALOG: 16 CatalogEntry em 5 categorias
|-- browser_extensions.py  # detect_installed_browsers + CATALOG extensoes + state
|-- window.py              # 4 tabs no Adw.ViewStack
`-- tabs/
    |-- browse.py          # catalogo categorizado + search + install/remove
    |-- pending.py         # lista pending_added/removed + botao Reiniciar
    |-- extensions.py      # extensoes por navegador detectado
    `-- about.py
```

### Catálogo de pacotes (5 categorias)

| Categoria | Pacotes |
|---|---|
| **Auditoria e hardening** | lynis, aide, chkrootkit, rkhunter |
| **Rede** | mtr, nethogs |
| **Monitoramento e diagnóstico** | lsof, strace, fail2ban |
| **Privacidade e criptografia** | wireguard-tools, dnscrypt-proxy |
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

### Pending changes via rpm-ostree status

```python
def pending_changes() -> PendingChanges:
    data = rpm_ostree_status_raw()  # rpm-ostree status --json
    booted = next((d for d in deployments if d.get("booted")), None)
    staged = next((d for d in deployments if d.get("staged")), None)
    if staged:
        staged_pkgs = set(staged.get("requested-packages", []) or [])
        booted_pkgs = set(booted.get("requested-packages", []) or [])
        pending_added = sorted(staged_pkgs - booted_pkgs)
        pending_removed = sorted(booted_pkgs - staged_pkgs)
```

## Comandos disparados

```bash
# Verificar instalacao
rpm -q lynis                         # returncode 0 = instalado

# Status do rpm-ostree (para deteccao de staged/pending)
rpm-ostree status --json

# Instalar (idempotente — nao falha se ja estiver staged)
pkexec rpm-ostree install --idempotent lynis aide chkrootkit

# Desinstalar
pkexec rpm-ostree uninstall lynis

# Aplicar mudancas
pkexec systemctl reboot

# Extensao: abrir URL no navegador default
xdg-open "https://addons.mozilla.org/firefox/addon/ublock-origin/"
xdg-open "https://chromewebstore.google.com/detail/cjpalhdlnbpafiamejdnhcphjbkeiagm"
```

## Tabs / Funcionalidades

| Tab | Descrição |
|---|---|
| **Catálogo** | Lista categorizada em `Adw.PreferencesGroup`. Cada item é `Adw.ExpanderRow` com prefix badge de status (`Disponivel` / `INSTALADO` / `PENDENTE`) + suffix botão ação (`Instalar` / `Remover` / `Pendente`). Expansão mostra `why` + nome do pacote. Status carregado em worker thread (`refresh_statuses_async`). Search filtra em nome/desc/pacote/why. |
| **Pendentes** | Hero "X pendentes" + grupos "Será instalado" / "Será removido no próximo boot" + botão `Reiniciar agora` (`pkexec systemctl reboot`). |
| **Extensões** | Detecta navegadores instalados, lista catálogo FOSS + botão "Abrir no <browser>" (xdg-open URL da AMO/Web Store). Marcação manual de "já instalei" persistente em JSON. Lock por categoria ad-blocker (só 1 por browser). |
| **Sobre** | 5 seções markup-formatted. |

## Quando usar

- **Setup pós-instalação**: instalar lynis + aide + chkrootkit em
  sequência, depois reiniciar 1x.
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

Install consolidado (`backend.py:122`):

```python
def install_packages_blocking(packages: list[str]) -> tuple[bool, str]:
    cmd = ["pkexec", "rpm-ostree", "install", "--idempotent"] + list(packages)
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
