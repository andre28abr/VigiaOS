# Instalar o VigiaOS — Fedora Silverblue (e atomic)

Vale para **Silverblue, Kinoite, Bluefin, Bazzite, Aurora** — qualquer
Fedora Atomic (usa `rpm-ostree`).

## Tudo de uma vez (recomendado)

```bash
curl -fsSL https://raw.githubusercontent.com/andre28abr/VigiaOS/main/install/bootstrap.sh | bash
systemctl reboot
```

O [`bootstrap.sh`](../bootstrap.sh) detecta sozinho que você está num
sistema atômico. Ele:

- layera as dependências (GTK4 + backends: `lynis`, `aide`, `clamav`, …)
  via `rpm-ostree`;
- clona o repo e instala as 16 ferramentas (`pip --user`) + atalhos no GNOME;
- instala Flatpaks de privacidade (KeePassXC, Signal, Tor Browser, …);
- **não liga nenhum serviço** — `tor`/`fail2ban`/`dnscrypt-proxy` ficam
  desligados; você ativa cada um na ferramenta correspondente quando quiser.

Como é sistema atômico, **reinicie no fim** pra os pacotes layered
ativarem. Depois é só abrir o **Vigia Hub** pelo menu do GNOME.

## Só um módulo (ex: só o Antivírus)

```bash
git clone https://github.com/andre28abr/VigiaOS.git ~/dev/VigiaOS
cd ~/dev/VigiaOS
install/install-tool.sh antivirus       # --list mostra os módulos
```

## Por que precisa de reboot?

Silverblue é atômico: pacotes do sistema entram em **camadas** que só
tomam efeito no próximo boot. As ferramentas Vigia em si (`pip --user`)
não precisam de reboot — mas os backends layered (`lynis`, `clamav`, …) sim.
