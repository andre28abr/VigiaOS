# Atualizações

## Em uma frase

Verifica e aplica atualizações do **sistema** e dos **programas da suíte
Vigia** via `dnf` — pelo painel (`pkexec dnf upgrade`) ou por um comando
copiável pro terminal. No VigiaOS aparece como a aba **Atualizações**
dentro de Configurações.

## O que envolve

| Item | Valor |
|---|---|
| **Pacote** | `vigia-tool-installer` |
| **App ID** | `br.com.vigia.ToolInstaller` |
| **Pacotes wrapped** | `dnf` |
| **Privilégios** | `pkexec dnf upgrade` (checagem `dnf check-update` sem root) |
| **Stack** | Python 3.11+ · PyGObject · GTK4 · libadwaita 1 |

## Arquitetura interna

```
vigia_installer/
|-- backend.py     # check_updates + update_command + split_updates + dnf upgrade
|-- catalog.py     # find_by_package + is_suite_package (rótulos amigáveis no split)
|-- window.py      # 2 tabs no Adw.ViewStack: Atualizações + Sobre
`-- tabs/
    |-- updates.py # checa/aplica updates do sistema (dnf)
    `-- about.py
```

> Histórico: esta área já foi um "Tool Installer" com catálogo de pacotes +
> extensões de navegador, num item próprio do rail. Foi simplificada para
> **só Atualizações + Sobre** e hoje é uma **aba dentro de Configurações** —
> o catálogo virou redundante (cada seção mostra a bolinha verde/vermelha
> de disponibilidade por módulo) e a instalação completa fica a cargo do
> `install/bootstrap.sh`.

### Checagem e aplicação de atualizações

```python
def check_updates() -> UpdateInfo:
    # dnf check-update  (rc 100 = update, 0 = nada, outro = erro)
    # parse_dnf_check_update extrai os nomes dos pacotes

def update_command(elevated=False) -> list[str]:
    # ["dnf","upgrade","-y"]; elevated=True prefixa "pkexec"
```

`check_updates()` é **read-only** (sem root), roda em worker thread ao abrir
(notificação no próprio painel). `run_system_update_blocking()` aplica via
`pkexec` (timeout 1800s). O comando copiável (`update_command_display()` →
`sudo dnf upgrade`) coexiste — painel vs terminal, o usuário escolhe.

A lista é **separada por origem**: **Sistema** vs **Programas da suíte Vigia**
(`split_updates` + `catalog.is_suite_package`).

## Comandos disparados

```bash
dnf check-update                # read-only; rc 100 = update, 0 = nada
pkexec dnf upgrade -y           # caminho "painel" (aplica na hora, sem reboot)
sudo dnf upgrade                # caminho "terminal" (copiável)
```

## Tabs

| Tab | Descrição |
|---|---|
| **Atualizações** | Checagem automática ao abrir (worker thread → hero "N atualizações" / "Sistema atualizado"). Botão `Atualizar agora` (`pkexec dnf upgrade -y`) + comando copiável. Lista separada: **Sistema** vs **Programas da suíte Vigia**. |
| **Sobre** | Seções markup explicando a área. |

## Limitações conhecidas

- A checagem depende do `dnf` (metadados de repositório atualizados).
- Aplicar pelo painel é bloqueante (a UI mostra o estado "Atualizando…").
