# Atualizações (`vigia-installer`)

A aba **Atualizações** do VigiaOS — fica em **Configurações → Atualizações**.
Checa e aplica updates do sistema e da suíte via `dnf`, com senha pedida uma
vez pelo Polkit (`pkexec`). Parte do [VigiaOS](../../README.md).

## O que faz

- **Checar** — roda `dnf check-update` (sem senha) e lista os pacotes com
  atualização pendente, separando **sistema** de **suíte Vigia** (rótulos
  amigáveis via `catalog.find_by_package` / `is_suite_package`).
- **Aplicar** — `pkexec dnf upgrade -y`, com progresso pulsante; aplica na hora,
  sem reboot.
- Alimenta o **sino de Notificações** e o painel **Tudo Certo?** da casca
  (item "atualizações").

## Histórico

Esta área já foi um **Tool Installer** com catálogo curado de pacotes de
segurança + extensões de navegador, num item próprio do Hub. Foi simplificada:
o catálogo virou redundante (cada seção já mostra a bolinha verde/vermelha de
disponibilidade por módulo e o comando de instalação) e a instalação completa
dos backends ficou a cargo de `install/bootstrap.sh`. O nome do pacote
(`vigia-installer`) ficou por compatibilidade.

## Como rodar

Normalmente embarcada no **VigiaOS** (Configurações → Atualizações). Sozinha:

```bash
cd tools/tool-installer
pip install --user -e .
vigia-installer
```

## Estrutura

```
tools/tool-installer/
├── pyproject.toml
├── data/
│   ├── br.com.vigia.ToolInstaller.svg
│   └── br.com.vigia.ToolInstaller.desktop
└── src/vigia_installer/
    ├── __init__.py / __main__.py / app.py
    ├── backend.py          # dnf wrapper (check-update / upgrade) — argv em lista, pkexec
    ├── catalog.py          # find_by_package + is_suite_package (rótulos no split sistema/suíte)
    ├── window.py           # 2 abas no Adw.ViewStack: Atualizações + Sobre
    └── tabs/
        ├── _helpers.py
        ├── updates.py      # hero card de atualizações + dnf upgrade
        └── about.py
```

## Atenção

- `dnf upgrade` aplica a mudança **na hora**, sem reboot.
- Para ver o histórico de transações: `dnf history` na CLI.

Manual técnico: [`docs/manuals/tecnico/tool-installer.md`](../../docs/manuals/tecnico/tool-installer.md).
