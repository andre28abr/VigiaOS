# Firewall Manager (firewall-gui)

## Em uma frase

Wrapper GTK4 do `firewall-cmd` que substitui o antigo `firewall-config`
— 2 tabs para gerenciar o daemon `firewalld`, zona padrão, e
services/portas permitidos por zona.

## O que envolve

| Item | Valor |
|---|---|
| **Pacotes Linux** | `firewalld`, `polkit` |
| **Comando principal** | `firewall-cmd --state`, `firewall-cmd --get-active-zones`, `pkexec firewall-cmd --permanent --add-service=ssh` |
| **Permissões** | Read-only roda como user. Write ops via `pkexec` |
| **Stack** | Python 3.11+ · PyGObject · GTK4 · libadwaita 1 |
| **Path config** | Sem state local — backend é o próprio `firewalld` (`/etc/firewalld/`) |
| **App ID** | `br.com.vigia.FirewallGui` |
| **Versão** | 0.1.0 |

## Arquitetura interna

```
vigia_firewall/
├── backend.py    — wraps firewall-cmd (read + pkexec write)
├── window.py     — build_content() monta ViewStack das 2 tabs
└── tabs/
    ├── status.py — daemon state + zona padrão + active zones
    └── zones.py  — services + portas customizadas por zona
```

Helper `_fw_cmd(*args)` roda `firewall-cmd` como user (read-only) e
devolve `(rc, stdout, stderr)` sem exception. Helper `_pkexec_fw(*args)`
roda com Polkit (write). Todas as write ops chamam `_reload()` ao final
(=`pkexec firewall-cmd --reload`) para aplicar imediatamente sem perder
o `--permanent`.

Todo subprocess vai pra `threading.Thread(daemon=True)` + `GLib.idle_add`
— Status faz 6+ firewall-cmd calls no refresh, todos paralelos em
background.

## Comandos disparados

```bash
# Status
firewall-cmd --state                       # running | not running
firewall-cmd --get-default-zone            # public, home, etc.
firewall-cmd --get-zones                   # lista de todas
firewall-cmd --get-active-zones            # quais estão em uso

# Daemon control
pkexec systemctl start firewalld.service
pkexec systemctl stop firewalld.service

# Zona padrão
pkexec firewall-cmd --set-default-zone=public

# Services por zona
firewall-cmd --zone=public --list-services
firewall-cmd --get-services                # universo de services disponíveis
pkexec firewall-cmd --permanent --zone=public --add-service=ssh
pkexec firewall-cmd --permanent --zone=public --remove-service=ssh
pkexec firewall-cmd --reload

# Portas por zona
firewall-cmd --zone=public --list-ports
pkexec firewall-cmd --permanent --zone=public --add-port=8080/tcp
pkexec firewall-cmd --permanent --zone=public --remove-port=8080/tcp
pkexec firewall-cmd --reload
```

## Tabs / Funcionalidades

### Status

- **Estado do firewalld**: label "ativo" (verde) / "parado" (vermelho)
  + botão Start/Stop (`pkexec systemctl`).
- **Zona padrão**: ComboRow com todas as zonas; mudança dispara
  `--set-default-zone`.
- **Zonas ativas**: lista de `--get-active-zones` parseado em
  `ActiveZone(name, interfaces, sources)`.

### Zonas

- **ComboRow zona**: escolhe qual zona editar.
- **Services permitidos**: lista de `--list-services` da zona. Botão
  "+ Adicionar" abre AlertDialog com DropDown de services disponíveis
  (diff de `--get-services` menos os já permitidos). Botão "Remover"
  por row → AlertDialog de confirmação (`destructive-action`).
- **Portas customizadas**: lista de `--list-ports` parseada em
  `PortRule(port, protocol)`. Botão "+ Adicionar" abre AlertDialog com
  Entry (porta ou range `8000-8010`) + DropDown TCP/UDP. Validação
  client-side: porta tem que ser digit+`-`, protocolo só tcp/udp.

Toda mudança é `--permanent --reload` — persiste no boot E aplica
agora. Não há opção "só runtime" deliberadamente (UX simples).

## Quando usar

- Verificar se o firewall está rodando antes de uma demonstração
  para cliente (tela inicial do Status verde = OK)
- Liberar SSH temporariamente para alguém debugar remoto: aba Zonas,
  zona `public`, "+ Adicionar service" → `ssh`
- Liberar porta de um app desenvolvido localmente: aba Zonas, "+
  Adicionar porta" → `8080/tcp`
- Trocar zona padrão de `public` para `home` ao chegar no escritório
  (mais permissivo internamente)

## Limitações conhecidas

- Sem editor visual de **rich rules** (rate-limit, log action,
  family=ipv6) — usar terminal.
- **ICMP block**, **masquerade**, **port-forwarding** ainda não
  expostos na GUI.
- Mudanças sempre escrevem `--permanent` + reload — não há toggle "só
  runtime" (decisão deliberada de UX).
- Não há criação/clone de zonas customizadas — só edição das default
  do Fedora.

## Trecho de código relevante

```python
# backend.py — helper para write ops (sempre permanent + reload)
def add_zone_service(zone: str, service: str) -> None:
    _pkexec_fw("--permanent", f"--zone={zone}", f"--add-service={service}")
    _reload()


def add_zone_port(zone: str, port: str, protocol: str) -> None:
    if protocol not in ("tcp", "udp"):
        raise ValueError(f"Protocolo invalido: {protocol}")
    if not port.replace("-", "").isdigit():
        raise ValueError(f"Porta invalida: {port}")
    _pkexec_fw("--permanent", f"--zone={zone}", f"--add-port={port}/{protocol}")
    _reload()


def _pkexec_fw(*args: str, timeout: int = 30) -> None:
    if shutil.which("pkexec") is None:
        raise RuntimeError("pkexec nao encontrado. Instale polkit.")
    result = subprocess.run(
        ["pkexec", "firewall-cmd"] + list(args),
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout).strip()
        if "Request dismissed" in stderr or result.returncode == 126:
            raise RuntimeError("Autenticacao cancelada pelo usuario.")
        raise RuntimeError(f"firewall-cmd {' '.join(args)} falhou: {stderr}")
```

```python
# backend.py — parser de --get-active-zones (formato indentado)
def get_active_zones() -> list[ActiveZone]:
    rc, out, _ = _fw_cmd("--get-active-zones")
    if rc != 0 or not out:
        return []
    zones: list[ActiveZone] = []
    current: ActiveZone | None = None
    for line in out.splitlines():
        if not line.startswith(" "):
            current = ActiveZone(name=line.strip(), interfaces=[], sources=[])
            zones.append(current)
        elif current is not None:
            line = line.strip()
            if line.startswith("interfaces:"):
                current.interfaces = line.split(":", 1)[1].strip().split()
            elif line.startswith("sources:"):
                current.sources = line.split(":", 1)[1].strip().split()
    return zones
```
