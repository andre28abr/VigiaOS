# Vigia Tool Installer

Catalogo curado de **ferramentas de seguranca** para Fedora Silverblue, com **one-click install** via `rpm-ostree`. Parte do [VigiaOS](../../README.md).

## Por que existe

Silverblue e' atomico: `dnf install` nao funciona — voce usa `rpm-ostree install` que cria uma camada e precisa de reboot. Os pacotes ficam pendentes ate reiniciar. Essa tool da:

- **Catalogo curado** (~22 ferramentas) com descricao em pt-BR e contexto ("por que voce quer isso")
- **Status visual** por item: disponivel / instalado / instalacao pendente / remocao pendente
- **One-click**: clica *Instalar* → polkit pede senha 1x → rpm-ostree stages a mudanca → tab *Pendentes* mostra com botao *Reiniciar*
- Sem precisar abrir terminal nem lembrar nomes de pacote

## Categorias do catalogo

| Categoria | Ferramentas |
|-----------|-------------|
| **Auditoria** | lynis, aide, chkrootkit, rkhunter |
| **Rede** | mtr, nethogs, iftop |
| **Monitoramento** | htop, iotop, lsof, strace, fail2ban |
| **Privacidade** | tor, torsocks, wireguard-tools, dnscrypt-proxy |
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
2. Clica `Instalar` → polkit pede senha (1x) → progress pulsante 1-5 min (rpm-ostree resolve deps + baixa + layer)
3. Status vira **PENDENTE** + badge amber
4. Vai pra aba **Pendentes** → ve a lista de mudancas pending
5. Clica `Reiniciar agora` → reboot
6. Apos boot, ferramenta esta disponivel no PATH

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
    ├── backend.py          # rpm-ostree wrapper
    ├── window.py
    └── tabs/
        ├── _helpers.py
        ├── browse.py       # catalogo categorizado + install/uninstall
        └── pending.py      # hero card de pending + reboot button
```

## Atencao

- `rpm-ostree install` modifica o sistema em camadas. **Sempre precisa reboot** para aplicar.
- Instalar muitos pacotes de uma vez **e' mais eficiente** que um por um — proximas versoes terao multi-select.
- Para reverter uma camada inteira sem desinstalar pacotes um por um: `rpm-ostree reset` (volta pra imagem base).
- Para ver o que esta layered no momento: `rpm-ostree status` na CLI.

## Roadmap (v0.2+)

- **Multi-select** com checkboxes + botao "Instalar selecionadas" (1 transacao rpm-ostree)
- Detecao de **dependencias recomendadas** (ex: clamav + clamtk juntos)
- **Search server-side** opcional (consultar dnf repos para pacotes nao curados)
- **Estatisticas**: tempo medio de instalacao, espaco usado por camada
- **Snapshots**: salvar uma combinacao instalada como "preset" (ex: preset "Forense", "Penetracao")
- **Verificacao de assinatura GPG** explicita antes de instalar (rpm-ostree ja faz, mas mostrar pro user)
- Integracao com **Activity Log**: mostra na timeline quando um install foi feito
