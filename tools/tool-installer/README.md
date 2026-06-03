# Vigia Tool Installer

Catalogo curado de **ferramentas de seguranca** para Fedora Workstation, com **one-click install** via `dnf`. Parte do [VigiaOS](../../README.md).

## Por que existe

Instalar ferramentas de seguranca pela CLI exige lembrar nomes de pacote e abrir terminal. Essa tool da:

- **Catalogo curado** (16 ferramentas) com descricao em pt-BR e contexto ("por que voce quer isso")
- **Status visual** por item: disponivel / instalado
- **One-click**: clica *Instalar* → polkit pede senha 1x → `dnf install -y` aplica na hora (sem reboot)
- Sem precisar abrir terminal nem lembrar nomes de pacote

## Categorias do catalogo

| Categoria | Ferramentas |
|-----------|-------------|
| **Auditoria** | lynis, aide, chkrootkit, rkhunter |
| **Rede** | mtr, nethogs |
| **Monitoramento** | lsof, strace, fail2ban |
| **Privacidade** | NetworkManager-openvpn-gnome, dnscrypt-proxy |
| **Forense** | clamav, hashdeep |

A lista esta em `src/vigia_installer/catalog.py` — adicionar uma tool nova e' apenas instanciar um `CatalogEntry`.

## Como rodar

```bash
cd tools/tool-installer
pip install --user -e .
vigia-installer
```

Ou via Vigia Hub.

## Fluxo tipico

1. **Catalogo** → procura uma ferramenta (search funciona por nome, pacote, descricao, "why")
2. Clica `Instalar` → polkit pede senha (1x) → progress pulsante 1-5 min (dnf resolve deps + baixa + instala)
3. `dnf install -y` aplica na hora — status vira **INSTALADO**
4. Ferramenta ja esta disponivel no PATH (sem reboot)

A aba **Atualizacoes** checa updates do sistema (`dnf check-update`) e aplica em 1 clique (`dnf upgrade -y`), tambem na hora.

## Estrutura

```
tools/tool-installer/
├── pyproject.toml
├── data/
│   ├── br.com.vigia.ToolInstaller.svg
│   └── br.com.vigia.ToolInstaller.desktop
└── src/vigia_installer/
    ├── __init__.py / __main__.py / app.py
    ├── catalog.py          # CatalogEntry dataclass + lista curada
    ├── backend.py          # dnf wrapper (install/remove/check-update/upgrade)
    ├── window.py
    └── tabs/
        ├── _helpers.py
        ├── browse.py       # catalogo categorizado + install/uninstall
        └── updates.py      # hero card de atualizacoes + dnf upgrade
```

## Atencao

- `dnf install` aplica a mudanca **na hora**, sem reboot.
- Instalar muitos pacotes de uma vez **e' mais eficiente** que um por um — proximas versoes terao multi-select.
- Para desinstalar um pacote: `sudo dnf remove <pkg>` (ou o botao *Remover* no catalogo).
- Para ver o historico de transacoes: `dnf history` na CLI.

## Roadmap (v0.2+)

- **Multi-select** com checkboxes + botao "Instalar selecionadas" (1 transacao dnf)
- Detecao de **dependencias recomendadas** (ex: clamav + clamtk juntos)
- **Search server-side** opcional (consultar dnf repos para pacotes nao curados)
- **Estatisticas**: tempo medio de instalacao, espaco usado por pacote
- **Snapshots**: salvar uma combinacao instalada como "preset" (ex: preset "Forense", "Penetracao")
- **Verificacao de assinatura GPG** explicita antes de instalar (dnf ja faz, mas mostrar pro user)
- Integracao com **Activity Log**: mostra na timeline quando um install foi feito
