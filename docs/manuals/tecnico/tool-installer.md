# Tool Installer

## Em uma frase

Catalogo curado de ~22 ferramentas de seguranca instalaveis com 1 clique
via `rpm-ostree` + catalogo de 8 extensoes FOSS para navegadores que
abrem em AMO/Chrome Web Store via `xdg-open`.

## O que envolve

| Item | Valor |
|---|---|
| **Pacote** | `vigia-tool-installer` (versao 0.2.0) |
| **App ID** | `br.com.vigia.ToolInstaller` |
| **Pacotes wrapped** | `rpm-ostree`, `xdg-open` |
| **Privilegios** | `pkexec rpm-ostree install/uninstall` |
| **State local** | `~/.config/vigia-installer/browser-extensions.json` |
| **Stack** | Python 3.11+ . PyGObject . GTK4 . libadwaita 1 |

## Arquitetura interna

```
vigia_installer/
|-- backend.py             # rpm-ostree install/uninstall/status/pending_changes
|-- catalog.py             # CATALOG: 22 CatalogEntry em 5 categorias
|-- browser_extensions.py  # detect_installed_browsers + CATALOG extensoes + state
|-- window.py              # 4 tabs no Adw.ViewStack
`-- tabs/
    |-- browse.py          # catalogo categorizado + search + install/remove
    |-- pending.py         # lista pending_added/removed + botao Reiniciar
    |-- extensions.py      # extensoes por navegador detectado
    `-- about.py
```

### Catalogo de pacotes (5 categorias)

| Categoria | Pacotes |
|---|---|
| **Auditoria e hardening** | lynis, aide, chkrootkit, rkhunter |
| **Rede** | mtr, nethogs, iftop |
| **Monitoramento e diagnostico** | htop, iotop, lsof, strace, fail2ban |
| **Privacidade e criptografia** | tor, torsocks, wireguard-tools, dnscrypt-proxy |
| **Forense e analise** | clamav, hashdeep |

Cada `CatalogEntry` tem `package`, `name`, `description` (1 linha),
`why` (paragrafo com markdown leve via `_md_to_pango`), `category`,
`binary` (para detecao). `by_category()` retorna agrupado preservando
ordem em `CATEGORIES_ORDER`.

### Catalogo de extensoes (8 FOSS)

| Extensao | Categoria | License | Firefox slug / Chrome ID |
|---|---|---|---|
| uBlock Origin | ad-blocker | GPL-3.0 | `ublock-origin` / `cjpalhdlnbpafiamejdnhcphjbkeiagm` |
| AdGuard AdBlocker | ad-blocker | GPL-3.0 | `adguard-adblocker` / `bgnkhhnnamicmpeenaelnjfhikgbkllg` |
| Privacy Badger | tracker-blocker | GPL-3.0 | `privacy-badger17` / `pkehgijcmpdhfbdbbnkijodmdjhbjlgp` |
| ClearURLs | url-cleaner | LGPL-3.0 | `clearurls` / `lckanjgmijmafbedllaakclkaicjfmnk` |
| LibRedirect | redirector | GPL-3.0 | `libredirect` / (so Firefox) |
| Cookie AutoDelete | cookie-manager | MIT | `cookie-autodelete` / `fhcgjolkccmbidfldomjliifgaodjagh` |
| Decentraleyes | cdn-cache | MPL-2.0 | `decentraleyes` / (so Firefox) |

Categoria `ad-blocker` esta em `EXCLUSIVE_CATEGORIES` — `find_conflicts()`
detecta se user ja marcou uBlock e esta tentando marcar AdGuard, dispara
dialog "Substituir uBlock?".

### Navegadores suportados

`detect_installed_browsers()` usa `shutil.which(binary)` para cada:
firefox, firefox-esr, librewolf, google-chrome, chromium-browser,
brave-browser, vivaldi. Familia firefox/chromium determina qual URL
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

| Tab | Descricao |
|---|---|
| **Catalogo** | Lista categorizada em `Adw.PreferencesGroup`. Cada item e' `Adw.ExpanderRow` com prefix badge de status (`Disponivel` / `INSTALADO` / `PENDENTE`) + suffix botao acao (`Instalar` / `Remover` / `Pendente`). Expansao mostra `why` + nome do pacote. Status carregado em worker thread (`refresh_statuses_async`). Search filtra em nome/desc/pacote/why. |
| **Pendentes** | Hero "X pendentes" + grupos "Sera instalado" / "Sera removido no proximo boot" + botao `Reiniciar agora` (`pkexec systemctl reboot`). |
| **Extensoes** | Detecta navegadores instalados, lista catalogo FOSS + botao "Abrir no <browser>" (xdg-open URL da AMO/Web Store). Marcacao manual de "ja instalei" persistente em JSON. Lock por categoria ad-blocker (so 1 por browser). |
| **Sobre** | 5 secoes markup-formatted. |

## Quando usar

- **Setup pos-instalacao**: instalar lynis + aide + chkrootkit em
  sequencia, depois reiniciar 1x.
- **Hardening incremental**: adicionar fail2ban quando comecar a expor
  servico SSH.
- **Privacidade browser**: instalar uBlock Origin + Privacy Badger +
  ClearURLs em Firefox novo.
- **Forense**: clamav + hashdeep para investigar maquina comprometida.

## Limitacoes conhecidas

- Sem multi-select (v0.2 roadmap: checkboxes + 1 transacao para varios
  pacotes simultaneos).
- Sem busca em repos externos — apenas o catalogo curado.
- Instalacoes com muitas dependencias podem demorar 5-10min.
- Extensoes nao tem deteccao real de "instalada no browser" — apenas
  marcacao manual em JSON local. CLI APIs do browser nao permitem instalar.
- `dnscrypt-proxy` no catalogo mas o DNS Manager v0.4 ja gerencia ele
  nativamente; instalar via Tool Installer e' redundante se ja usa o DNS Manager.

## Trecho de codigo relevante

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
