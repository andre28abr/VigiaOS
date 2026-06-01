"""Catalogo de extensoes open source pra navegadores + state local.

Limitacao tecnica importante: nao podemos instalar/desinstalar extensoes
via CLI. Firefox/Chrome/Brave fazem instalacao via flow proprio do
navegador (com confirmation dialog). O que esta tool faz:

1. Detecta quais navegadores estao instalados na maquina
2. Mostra catalogo curado de extensoes open source
3. Botao 'Abrir no Firefox' / 'Abrir no Chrome' executa xdg-open na URL
   da AMO / Chrome Web Store — navegador toma de la
4. Mantem state LOCAL (~/.config/vigia-installer/extensions.json) com
   quais extensoes o user 'marcou como instalada'
5. Lock por categoria: apenas 1 ad-blocker marcado por vez
   (uBlock vs AdGuard conflitam se ativos ao mesmo tempo).
   Quando user marca segundo, dialog 'substituir uBlock?'.

Extensoes recomendadas — apenas FOSS, todas mantidas e disponiveis na
AMO (Mozilla Add-ons) e Chrome Web Store (quando aplicavel).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


STATE_PATH = Path.home() / ".config" / "vigia-installer" / "browser-extensions.json"


@dataclass
class BrowserInfo:
    """Browser detectado no sistema."""
    id: str               # 'firefox', 'chrome', 'brave', 'chromium', 'vivaldi'
    label: str            # 'Mozilla Firefox'
    binary: str           # binary name (`firefox`, `google-chrome`)
    family: str           # 'firefox' ou 'chromium'
    flatpak_id: str = ""  # flatpak ref (opcional, futuro)


SUPPORTED_BROWSERS: list[BrowserInfo] = [
    BrowserInfo(
        id="firefox", label="Mozilla Firefox", binary="firefox",
        family="firefox", flatpak_id="org.mozilla.firefox",
    ),
    BrowserInfo(
        id="firefox-esr", label="Firefox ESR", binary="firefox-esr",
        family="firefox",
    ),
    BrowserInfo(
        id="librewolf", label="LibreWolf", binary="librewolf",
        family="firefox", flatpak_id="io.gitlab.librewolf-community",
    ),
    BrowserInfo(
        id="chrome", label="Google Chrome", binary="google-chrome",
        family="chromium",
    ),
    BrowserInfo(
        id="chromium", label="Chromium", binary="chromium-browser",
        family="chromium", flatpak_id="org.chromium.Chromium",
    ),
    BrowserInfo(
        id="brave", label="Brave Browser", binary="brave-browser",
        family="chromium", flatpak_id="com.brave.Browser",
    ),
    BrowserInfo(
        id="vivaldi", label="Vivaldi", binary="vivaldi",
        family="chromium",
    ),
]


@dataclass
class BrowserExtension:
    """Extensao curada disponivel pra recomendar."""
    id: str                  # ID interno (slug)
    name: str                # display name
    description: str         # 1-2 linhas curtas
    why: str                 # paragrafo explicando privacidade
    category: str            # 'ad-blocker', 'tracker-blocker', 'url-cleaner',
                             # 'cdn-cache', 'redirector', 'cookie-manager'
    license: str             # ex: 'GPL-3.0', 'LGPL-3.0', 'MPL-2.0', 'MIT'
    homepage: str            # URL do projeto
    firefox_slug: str = ""   # slug em addons.mozilla.org (vazio = nao tem)
    chrome_id: str = ""      # ID na chrome web store (vazio = nao tem)
    recommended: bool = False  # destaque visual


# v0.4: catalogo inicial — todas FOSS, todas mantidas
CATALOG: list[BrowserExtension] = [
    BrowserExtension(
        id="ublock-origin",
        name="uBlock Origin",
        description="Ad/tracker blocker open source — o melhor do mercado.",
        why=(
            "Bloqueia anúncios, trackers, malware e popups com filtros "
            "atualizados pela comunidade (EasyList + outras). Esconde o "
            "elemento (sem buraco no layout), anti-anti-adblock, whitelist "
            "por site em 1 clique. Mantido pelo Raymond Hill, sem dono "
            "comercial, sem versão paga. **Recomendado** pra todos os "
            "usuários."
        ),
        category="ad-blocker",
        license="GPL-3.0",
        homepage="https://github.com/gorhill/uBlock",
        firefox_slug="ublock-origin",
        chrome_id="cjpalhdlnbpafiamejdnhcphjbkeiagm",
        recommended=True,
    ),
    BrowserExtension(
        id="adguard-adblocker",
        name="AdGuard AdBlocker",
        description="Alternativa ao uBlock — feita pela empresa AdGuard.",
        why=(
            "Empresa AdGuard, listas próprias + EasyList. Feature-rich, "
            "mas a empresa também vende produtos pagos (DNS, Family Mode). "
            "A extensão em si é GPL-3.0. Use se preferir o ecossistema "
            "AdGuard, mas **uBlock Origin geralmente é mais leve** e "
            "completamente independente."
        ),
        category="ad-blocker",
        license="GPL-3.0",
        homepage="https://github.com/AdguardTeam/AdguardBrowserExtension",
        firefox_slug="adguard-adblocker",
        chrome_id="bgnkhhnnamicmpeenaelnjfhikgbkllg",
    ),
    BrowserExtension(
        id="privacy-badger",
        name="Privacy Badger (EFF)",
        description="Detecta e bloqueia trackers automaticamente.",
        why=(
            "Da Electronic Frontier Foundation. Diferente de adblockers "
            "tradicionais, aprende com seu comportamento — bloqueia "
            "trackers que seguem você por 3+ sites. Bom **complemento** "
            "ao uBlock (não substitui)."
        ),
        category="tracker-blocker",
        license="GPL-3.0",
        homepage="https://privacybadger.org/",
        firefox_slug="privacy-badger17",
        chrome_id="pkehgijcmpdhfbdbbnkijodmdjhbjlgp",
    ),
    BrowserExtension(
        id="clearurls",
        name="ClearURLs",
        description="Remove tracking parameters das URLs.",
        why=(
            "Limpa `?utm_source=...`, `?fbclid=...`, `?gclid=...` e "
            "centenas de outros parâmetros de tracking. Funciona em "
            "background, sem UI. Bom **complemento** ao uBlock."
        ),
        category="url-cleaner",
        license="LGPL-3.0",
        homepage="https://gitlab.com/KevinRoebert/ClearUrls",
        firefox_slug="clearurls",
        chrome_id="lckanjgmijmafbedllaakclkaicjfmnk",
    ),
    BrowserExtension(
        id="libredirect",
        name="LibRedirect",
        description="Redireciona YouTube/Twitter/Reddit pra alternativas privadas.",
        why=(
            "YouTube -> Invidious, Twitter -> Nitter, Reddit -> Redlib, "
            "etc. As alternativas são **frontends abertos** que não usam "
            "tracking, não precisam de conta, e quebram ad-revenue dos "
            "originais. Você configura quais redirecionar."
        ),
        category="redirector",
        license="GPL-3.0",
        homepage="https://libredirect.github.io/",
        firefox_slug="libredirect",
        # LibRedirect nao esta na Chrome Web Store oficialmente
        chrome_id="",
    ),
    BrowserExtension(
        id="cookie-autodelete",
        name="Cookie AutoDelete",
        description="Apaga cookies de sites não-whitelistados.",
        why=(
            "Quando você fecha uma aba, todos os cookies do site são "
            "apagados — exceto sites na sua whitelist (gmail, banco, "
            "etc). Bom pra **quebrar persistent tracking** sem perder "
            "logins importantes."
        ),
        category="cookie-manager",
        license="MIT",
        homepage="https://github.com/Cookie-AutoDelete/Cookie-AutoDelete",
        firefox_slug="cookie-autodelete",
        chrome_id="fhcgjolkccmbidfldomjliifgaodjagh",
    ),
    BrowserExtension(
        id="decentraleyes",
        name="Decentraleyes",
        description="Cache local de CDNs (jQuery, Google Fonts, etc.).",
        why=(
            "Quando um site carrega jQuery do Google CDN, o Google sabe "
            "que você visitou esse site. Decentraleyes serve esses "
            "recursos do disco local — Google não vê. **Privacy + "
            "velocidade**."
        ),
        category="cdn-cache",
        license="MPL-2.0",
        homepage="https://decentraleyes.org/",
        firefox_slug="decentraleyes",
        chrome_id="",  # versao chrome nao eh oficial
    ),
]


# ============================================================
# Categorias com restricao de unicidade
# ============================================================

# Categorias onde so deveria ter 1 marcado por vez (conflito)
EXCLUSIVE_CATEGORIES = {"ad-blocker"}

CATEGORY_LABELS = {
    "ad-blocker": "Ad/tracker blocker",
    "tracker-blocker": "Anti-tracking",
    "url-cleaner": "URL cleaner",
    "redirector": "Redirector privado",
    "cookie-manager": "Cookie manager",
    "cdn-cache": "Cache local de CDN",
}


# ============================================================
# Detecao de browsers
# ============================================================


def detect_installed_browsers() -> list[BrowserInfo]:
    """Lista browsers detectados via `which`."""
    out: list[BrowserInfo] = []
    for b in SUPPORTED_BROWSERS:
        if shutil.which(b.binary) is not None:
            out.append(b)
    return out


# ============================================================
# State local (marcacao manual do user)
# ============================================================


def _load_state() -> dict:
    """Le state file. Retorna {} se nao existe ou erro."""
    if not STATE_PATH.exists():
        return {"installed": {}}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"installed": {}}
    # HARDENING: arquivo editavel/corrompivel — garante dict.
    return data if isinstance(data, dict) else {"installed": {}}


def _save_state(state: dict) -> None:
    """Salva state em ~/.config/vigia-installer/."""
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.parent.chmod(0o700)  # LGPD: dir restrita ao dono
        STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
        STATE_PATH.chmod(0o600)         # LGPD: metadado de privacidade do usuario
    except OSError as e:
        print(f"[browser_extensions] save_state falhou: {e}", flush=True)


def get_installed(ext_id: str) -> list[str]:
    """Retorna lista de browser ids onde a extensao foi marcada."""
    installed = _load_state().get("installed", {})
    if not isinstance(installed, dict):
        return []
    val = installed.get(ext_id, [])
    return val if isinstance(val, list) else []


def is_marked_installed(ext_id: str, browser_id: str) -> bool:
    return browser_id in get_installed(ext_id)


def mark_installed(ext_id: str, browser_id: str) -> None:
    """Marca extensao como instalada num browser."""
    state = _load_state()
    state.setdefault("installed", {})
    browsers = state["installed"].get(ext_id, [])
    if browser_id not in browsers:
        browsers.append(browser_id)
    state["installed"][ext_id] = browsers
    _save_state(state)


def unmark_installed(ext_id: str, browser_id: str) -> None:
    """Desmarca extensao."""
    state = _load_state()
    if "installed" not in state:
        return
    browsers = state["installed"].get(ext_id, [])
    if browser_id in browsers:
        browsers.remove(browser_id)
    if browsers:
        state["installed"][ext_id] = browsers
    else:
        state["installed"].pop(ext_id, None)
    _save_state(state)


def find_conflicts(ext_id: str, browser_id: str) -> list[str]:
    """Acha extensoes ja marcadas no mesmo browser em categoria exclusiva.

    Usado pra detectar 'user ja tem uBlock marcada, esta tentando marcar
    AdGuard'. Retorna lista de ext_ids conflitantes (pode ter mais de 1).
    """
    ext = find_extension(ext_id)
    if ext is None or ext.category not in EXCLUSIVE_CATEGORIES:
        return []

    state = _load_state()
    installed_map = state.get("installed", {})
    conflicts = []
    for other_id, browsers in installed_map.items():
        if other_id == ext_id:
            continue
        if browser_id not in browsers:
            continue
        other = find_extension(other_id)
        if other is None:
            continue
        if other.category == ext.category:
            conflicts.append(other_id)
    return conflicts


def find_extension(ext_id: str) -> BrowserExtension | None:
    for e in CATALOG:
        if e.id == ext_id:
            return e
    return None


# ============================================================
# Abrir URL da extensao no browser
# ============================================================


def url_for(ext: BrowserExtension, browser: BrowserInfo) -> str | None:
    """URL pra instalar a extensao no browser. None se indisponivel."""
    if browser.family == "firefox" and ext.firefox_slug:
        return f"https://addons.mozilla.org/firefox/addon/{ext.firefox_slug}/"
    if browser.family == "chromium" and ext.chrome_id:
        return f"https://chromewebstore.google.com/detail/{ext.chrome_id}"
    return None


def open_in_browser(ext: BrowserExtension, browser: BrowserInfo) -> tuple[bool, str]:
    """Abre URL da extensao no browser usando xdg-open.

    Nao usa o `browser.binary` direto — usa xdg-open pra respeitar o
    default browser do user. Mas a URL leva pra AMO ou Chrome Web Store
    do tipo certo (firefox-family ou chromium-family).
    """
    url = url_for(ext, browser)
    if url is None:
        return False, f"Extensão não disponível pra {browser.label}."
    try:
        subprocess.run(["xdg-open", url], timeout=5, check=False)
        return True, ""
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return False, f"Falha ao abrir browser: {e}"
