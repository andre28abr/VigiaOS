# Instalar o VigiaOS — Fedora Workstation (tradicional)

Para o Fedora **Workstation** clássico (não-atômico, usa `dnf`).

## Tudo de uma vez (recomendado)

```bash
curl -fsSL https://raw.githubusercontent.com/andre28abr/VigiaOS/main/install/bootstrap.sh | bash
```

O [`bootstrap.sh`](../bootstrap.sh) detecta sozinho que você está num
sistema tradicional. Ele:

- instala as dependências (GTK4 + backends: `lynis`, `aide`, `clamav`, …)
  via `dnf`;
- clona o repo e instala as 16 ferramentas (`pip --user`) + atalhos no GNOME;
- instala Flatpaks de privacidade (KeePassXC, Signal, Tor Browser, …);
- **não liga nenhum serviço** — `tor`/`fail2ban`/`dnscrypt-proxy` ficam
  desligados; opt-in nas ferramentas.

**Sem reboot** — o `dnf` aplica na hora. Abra o **Vigia Hub** pelo menu
do GNOME (ou rode `vigia-hub`).

## Só um módulo (ex: só o Antivírus)

```bash
git clone https://github.com/andre28abr/VigiaOS.git ~/dev/VigiaOS
cd ~/dev/VigiaOS
install/install-tool.sh antivirus       # --list mostra os módulos
```

## Diferenças em relação ao Silverblue

- Pacotes via `dnf` (na hora, sem reboot) em vez de `rpm-ostree`
  (camadas + reboot).
- O **Deployments Manager** não aparece no Hub — ele gerencia deployments
  `rpm-ostree`, que não existem no Workstation.
- No Tool Installer não há aba "Pendentes" (o `dnf` aplica na hora).
