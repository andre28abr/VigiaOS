# Activity Log

## Pra que serve

O **Activity Log** é o **"caderno de bordo"** do seu computador. Tudo o que acontece no sistema — você ligando uma câmera, alguém tentando entrar via SSH, um programa morrendo de falta de memória, o firewall bloqueando alguma coisa — fica registrado em arquivos do Linux que são **brutos e impossíveis de ler**. O Activity Log pega esses arquivos, **traduz pra português** e mostra numa linha do tempo organizada.

É como se você tivesse um leitor inteligente das câmeras de segurança da sua casa: em vez de te mostrar "Frame 0x2A1 detectado em zona 4 com confidence 0.87", ele te diz "Alguém passou pela cozinha às 14:32, voltou às 14:35".

## Quando você usa isso

- Você notou que o computador está lento ou estranho e quer entender **o que aconteceu nos últimos minutos**
- Você desconfia que alguém tentou invadir via internet
- Você precisa de **prova** pra LGPD ou auditoria de quem acessou o sistema e quando
- Algum programa parou de funcionar e você quer saber se foi o SELinux que bloqueou
- Você tem um servidor e quer ver se o fail2ban está banindo IPs maliciosos

## O que você vai ver

Quando você abre, ele está vazio. Você **clica no botão "Atualizar"** (ícone de seta circular, em cima à direita) e ele vai buscar os eventos. Aparece uma barra azul piscando enquanto ele trabalha.

Em cima tem um switch **"Admin"** — se você ligar e digitar sua senha, ele acessa **muito mais eventos** (incluindo coisas do sistema, não só do seu usuário).

## O que cada parte faz

### Aba 1 — Status

Mostra um **resumo** do que foi coletado: quantos eventos achou, quantos são **suspeitos**, quantos **interessantes**, quantos são **rotina** (chatos), quantas **correlações** detectou, e em que horário foi gerado. Tipo o resumo no topo de um relatório.

### Aba 2 — Timeline

A **linha do tempo de tudo**. Cada linha tem o horário, de qual sistema veio (audit, journal, fail2ban) e o que aconteceu, escrito em **português**. Você pode buscar texto, filtrar por gravidade ou por fonte.

Os textos são do tipo:

> *14:32:18 [journal] Usuário joao fez login na sessão gráfica*
>
> *14:33:01 [fail2ban] IP 192.0.2.42 banido por 3600s (tentou SSH 5 vezes)*

### Aba 3 — Correlações

A parte **mais inteligente**. Em vez de te mostrar 50 linhas separadas dizendo "tentou SSH", "tentou SSH", "tentou SSH", "baniu IP", ele **agrupa tudo** numa frase só:

> *"fail2ban baniu 192.0.2.42 após 5 tentativas em 12s (jail sshd)"*

Tem 4 padrões detectados automaticamente:

1. **Brute-force de SSH** — alguém tentando adivinhar sua senha várias vezes, e o fail2ban banindo
2. **Programa morto por falta de memória** (OOM kill) — quando o Chrome come 8GB e o Linux mata ele
3. **SELinux bloqueando algo várias vezes** — geralmente sinal de configuração quebrada (não é ataque)
4. **Login SSH após tentativas falhas** — login aceito de um IP que tinha tentado falhar antes (suspeito)

### Aba 4 — Sobre

Versão do programa e dos arquivos que ele lê.

## Termos que você vai ver

- **Audit** — sistema de auditoria do kernel Linux. Registra coisas profundas como SELinux, syscalls, mudanças de permissão. Arquivo em `/var/log/audit/audit.log`.
- **Journal (journald)** — o "diário" do systemd. Registra **tudo** o que o sistema e os serviços fazem (login, inicialização, erros).
- **fail2ban** — vigia automático que bane IPs que tentam te invadir por SSH (tipo um "porteiro" que banca o suspeito).
- **Severidade** — gravidade do evento: **routine** (chato, comum), **interesting** (vale uma olhada) ou **suspicious** (atenção, pode ser problema).

## Posso quebrar alguma coisa?

**Não.** O Activity Log é **somente leitura**. Ele apenas **abre arquivos** que já existem no sistema e te mostra. Não apaga, não edita, não envia nada pra fora do seu computador.

Mesmo o **modo Admin** só precisa de senha porque alguns desses arquivos são **protegidos por padrão** (só root lê). A senha é usada **uma única vez por atualização** — não fica salva em lugar nenhum.

## Dica do dia

> Sempre que algo "estranho" acontecer (programa fechou sozinho, alerta apareceu, computador travou), abra o Activity Log, ligue o **Admin**, clique **Atualizar** e vá direto pra aba **Correlações**. Se algo importante rolou, vai estar lá em UMA FRASE em português. Você não precisa virar especialista em logs.

## Onde encontrar mais

Os arquivos originais que esta tool lê ficam em:

- **Audit** (kernel + SELinux): `/var/log/audit/audit.log`
- **Journal** (serviços do sistema): use `journalctl` no terminal
- **fail2ban** (banimentos): `/var/log/fail2ban.log`

Mas você não precisa abrir nenhum disso — pra isso existe o Activity Log.
