# Casca do VigiaOS (`vigia-hub`)

> A **casca** (shell) do **VigiaOS**: um único app GTK4 + libadwaita que
> reúne todas as ferramentas numa janela só. O pacote ainda se chama
> `vigia-hub` por herança — hoje ele é o app inteiro, não só o launcher.

## Estado

🟢 **v0.12.6** — rail de **5 seções**:

| Seção | O que mostra |
|---|---|
| **Início** | Monitor do Sistema em tela cheia (a tool `dashboard`, promovida pra cá) |
| **Hub** | Master-detail com as **13 ferramentas** do catálogo (`registry.py`), agrupadas por categoria; a primeira é o **Tudo Certo?** (checkup 🟢🟡🔴) |
| **Red** | Módulos de pentest do `vigia-red` (4 prontos, 3 planejados) atrás de um termo de uso |
| **Blue** | Módulos de SOC do `vigia-blue` (7 prontos) |
| **Relatórios** | **Central de Relatórios** — eventos gravados pelas ferramentas (`vigia_common.events`, SQLite `0600`, retenção 180 dias), filtros 7/30/90/365 dias, exportação HTML com selo SHA-256 |

No rodapé do rail: **Configurações** (abas Sobre · Atualizações · Aplicação ·
Segurança · Ajuda) e o sino de **Notificações**. A **Ajuda** carrega os manuais
leigos e técnicos de `docs/manuals/` dentro do app.

Recursos da casca: busca rápida `Ctrl+K`, tema Terminal opcional, notificações
de segurança, varredura de vírus semanal (timer systemd do usuário), autostart
XDG, ícone na bandeja (subprocess GTK3), bloqueio por senha via Polkit,
backup/restauração da configuração (`.zip` `0600`).

## Como funciona

`src/vigia_hub/registry.py` contém a lista `TOOLS` de `ToolEntry`. Cada entry
declara `id`, `name`, `description`, `long_description`, `features`,
`icon_path`, `category`, `wrapped_packages`, `available_fn` (checa se o
backend existe) e, principalmente, **`embedded_module`** — o módulo Python
cuja função `build_content()` devolve o widget que a casca embute no painel
de conteúdo (import lazy, widget cacheado entre trocas).

Red e Blue não têm `ToolEntry` próprio: seus módulos (`Module`, em
`vigia_common.shell`) entram pelo **mesmo master-detail** via um adaptador
`Module → ToolEntry`. A bolinha de disponibilidade nesses casos é **por
dependência** (`Module.requires`), e a aba *Instalador* mostra o comando de
instalação de cada uma.

Escalada de privilégio é sempre **dentro de cada ferramenta**, via `pkexec`
(diálogo Polkit) — a casca nunca prefixa `sudo` em nada.

## Adicionar uma ferramenta nova ao Hub

Em `src/vigia_hub/registry.py`, acrescente um `ToolEntry` apontando
`embedded_module` para o módulo que expõe `build_content()`; escolha a
`category` entre as de `CATEGORIES_ORDER`. Roteiro completo (pyproject,
ícone, manuais leigo/técnico, testes) em
[DEVELOPMENT.md §7](../../DEVELOPMENT.md#7-como-adicionar-uma-ferramenta-nova).

Reabra o **VigiaOS** (não só a ferramenta — ela roda embarcada) e ela aparece
na lista.

## Setup

O jeito recomendado é `install/bootstrap.sh` (ou `install/vigia-setup.sh`),
que instala tudo em editable mode e registra o `.desktop` do app
(`data/br.com.vigia.OS.desktop`) + ícone no menu do GNOME. Só o pacote, à mão:

```bash
cd ~/dev/VigiaOS/tools/vigia-hub
pip install --user -e .
vigia-os          # aliases: vigia-hub / vigia-red / vigia-blue abrem já na seção
```

## Roadmap

Ver [DEVELOPMENT.md §10](../../DEVELOPMENT.md#10-roadmap).
