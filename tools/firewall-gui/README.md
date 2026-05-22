# Vigia Firewall GUI

> Gerenciador GTK4 + libadwaita para **firewalld**. Substitui o `firewall-config`
> antigo, complementa o ON/OFF do Privacy Controls.

## Estado

🟡 **v0.1 MVP** — duas tabs cobrindo as operações mais comuns.

### Status
- **Daemon**: rodando ou parado (cor: verde/vermelho)
- **Botão Start/Stop** via `pkexec systemctl`
- **Zona padrão** com combo dropdown para mudar via `firewall-cmd --set-default-zone`
- **Zonas ativas**: lista com interfaces e sources por zona

### Zonas
- Combo para escolher zona a editar (public, internal, dmz, drop, trusted, etc.)
- **Services nesta zona**: lista de services permitidos + botão "Adicionar"
  (mostra dropdown com services pré-definidos do firewalld que ainda não foram permitidos)
- **Portas nesta zona**: lista de port rules customizadas + "Adicionar" (porta + protocolo)
- Botão "Remover" em cada service/porta

Todas as mudanças escrevem **`--permanent` + `--reload`** (persistem no boot E aplicam imediatamente).

## Setup

```bash
cd ~/dev/VigiaOS/tools/firewall-gui
pip install --user -e .
vigia-firewall
```

Instalar entry GNOME:
```bash
mkdir -p ~/.local/share/applications ~/.local/share/icons/hicolor/scalable/apps
cp data/br.com.vigia.FirewallGui.desktop ~/.local/share/applications/
cp data/br.com.vigia.FirewallGui.svg ~/.local/share/icons/hicolor/scalable/apps/
gtk-update-icon-cache ~/.local/share/icons/hicolor 2>/dev/null || true
update-desktop-database ~/.local/share/applications 2>/dev/null || true
```

## Limitações v0.1

- **Sem rich rules** — regras avançadas (`rate-limit`, `log` action, `family=ipv6`) ficam para v0.2.
- **Sem masquerade/port-forwarding** — NAT/forwarding em v0.2.
- **Sem ICMP block** — controle de tipos ICMP em v0.2.
- **Cada operação pede senha (pkexec sem cache)** — D-Bus + polkit cache em v0.3 da suite.
- **Sem editor de service** — criar service customizado (não os 100+ pré-definidos)
  exige editar XML em `/etc/firewalld/services/` manualmente.

## Roadmap

- ✅ v0.1: Status + Zones (services + ports CRUD)
- v0.2: Rich rules, ICMP block, masquerade, port forwarding
- v0.3: D-Bus + polkit cache (auth_admin_keep), service editor
- v0.4: Profiles (presets como "Modo trabalho", "Modo público", "Modo paranoia")
- v0.5: Integração com Activity Log (clique em conexão bloqueada → vai pra Zona certa)
