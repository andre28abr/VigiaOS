# Privacy Controls

## Pra que serve

O **Privacy Controls** é um **painel de interruptores**. Cada interruptor liga ou desliga uma configuração de privacidade do seu computador — coisas como **GPS**, **histórico de arquivos abertos**, **firewall**, **Bluetooth** e **prévia de mensagens na tela bloqueada**.

Sem essa ferramenta, você teria que abrir o Settings do GNOME, depois o dconf-editor, depois o terminal pra mexer em systemd, depois o gnome-tweaks... pra ligar coisas que ficam **espalhadas em uns 5 lugares diferentes**. Aqui está **tudo numa tela só**.

Imagine um **painel elétrico de casa** — todos os disjuntores no mesmo quadro. Você não precisa correr nos cômodos pra desligar a luz, está tudo ali.

## Quando você usa isso

- Você **acabou de instalar o sistema** e quer ajustar privacidade rápido
- Vai usar a máquina num café ou rede pública — quer **ligar firewall**, **desligar SSH**, **desligar Bluetooth**
- Trabalha com **dados sensíveis** (advocacia, medicina, contabilidade) e precisa demonstrar **conformidade LGPD**
- Quer **esconder prévias** das suas notificações quando você trava a tela (pra ninguém ler seus whatsapps por cima do seu ombro)
- Vai emprestar o computador pra alguém e quer **não deixar rastros** do que você andou usando

## O que você vai ver

Uma **lista de interruptores** organizados em **grupos**:

- **Localização**
- **Telemetria** (relatórios automáticos do sistema)
- **Histórico** (arquivos abertos recentes, uso de apps, metadados de identidade)
- **Lock Screen** (bloqueio automático, prévia de notificações)
- **Limpeza Automática** (lixeira e arquivos temporários)
- **Rede** (firewall, servidor SSH)
- **Dispositivos** (Bluetooth)

Cada interruptor tem um **nome** em cima e uma **explicação** embaixo dizendo **o que muda quando você liga ou desliga**.

Se algum interruptor estiver **acinzentado**, significa que ele **não funciona** no seu sistema (por exemplo, Bluetooth desabilitado se o PC não tem adaptador Bluetooth).

## O que cada parte faz

### Aba 1 — Toggles

A tela principal com todos os interruptores. Você **clica** num interruptor pra mudar o estado. As mudanças **acontecem na hora**:

- Pros **toggles do GNOME** (localização, telemetria, etc) — muda direto, sem pedir senha
- Pros **toggles de Rede** — pede sua **senha de admin** antes de mexer (porque mudar firewall ou ligar SSH afeta o sistema inteiro)

Quando você desliga "Serviços de localização", **na mesma hora** apps GNOME perdem acesso a GPS, redes Wi-Fi próximas e geolocalização por IP. Você pode abrir o Settings do GNOME ao lado e ver os switches mudando juntos.

### Aba 2 — Sobre

Versão do programa e onde ficam as configurações salvas.

## Termos que você vai ver

- **Telemetria** — relatórios automáticos que o GNOME envia pros desenvolvedores sobre crashes e uso. Desligar = privacidade aumenta, GNOME não fica sabendo.
- **Firewall (firewalld)** — o "porteiro" do seu PC. Quando ligado, ele decide quais conexões de fora podem entrar. Quando desligado, qualquer um na sua rede pode tentar.
- **SSH** — protocolo pra acessar seu PC de outro computador via terminal. **Desligado por padrão** é o mais seguro.
- **dconf** — banco de dados onde o GNOME guarda suas preferências. Os toggles do GNOME aqui escrevem direto lá.

## Posso quebrar alguma coisa?

**Algumas opções têm efeitos significativos:**

- **Desligar o Firewall** te deixa **exposto** em redes não-confiáveis. Use só em casa numa rede sua. Em café, hotel, qualquer rede pública — mantenha **ligado**.
- **Ligar o SSH** abre a porta 22 do seu PC pra **conexões recebidas** do mundo. Se você não tem motivo claro (acessar seu PC de outro lugar), mantenha **desligado**.
- **Ligar o Tor** só inicia o serviço local — **não roteia** automaticamente seu Firefox/Chrome pelo Tor. Pra navegação anônima, use o **Tor Browser** separado.

Os outros toggles (GNOME) são todos **reversíveis sem dor** — você só liga e desliga, sem efeitos colaterais.

## Dica do dia

> Quando você for trabalhar num **café ou rede pública**, abra o Privacy Controls e siga esse "checklist":
>
> 1. **Firewall** — ligado
> 2. **Servidor SSH** — desligado
> 3. **Bluetooth** — desligado (a menos que precise do mouse Bluetooth)
> 4. **Esconder prévia de notificações na lock screen** — ligado
>
> Leva 10 segundos. Quando voltar pra casa, faz o reverso se quiser.

## Onde encontrar mais

Esta ferramenta não **inventa** configurações — ela apenas mexe nas mesmas chaves que o **GNOME Settings** e o `systemctl` já usam. Se você desligar algo aqui e abrir o GNOME Settings, vai ver o switch de lá também desligado. São a mesma configuração mostrada em dois lugares.

O que muda é a **conveniência**: aqui está tudo agrupado em uma tela só, focado em **privacidade**.
