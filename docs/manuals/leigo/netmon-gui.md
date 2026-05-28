# Monitor de Rede

## Pra que serve

Sabe quando você tá em casa e quer saber **quem está usando a
internet** naquele momento? Tipo "será que o vídeo está pesando
porque alguém está baixando coisa?".

O **Monitor de Rede** é isso, mas pra **dentro do computador**.
Ele mostra, em tempo real:

- Quais programas estão **conectados a sites/serviços** agora
- Quais programas estão **esperando conexões** chegarem
- Em quais portas/endereços essas conexões estão acontecendo

É como ter uma janelinha vendo a "fofoca" da rede do seu computador.

## Quando você usa isso

Algumas situações úteis:

1. **"Tem alguma coisa estranha acontecendo na rede"** — você abre
   e procura conexões que não esperava. Tipo um programa conversando
   com IP estrangeiro que você não conhece.

2. **"Esse programa está usando internet?"** — filtra pelo nome do
   programa (ex: "firefox") e vê com quem ele está conversando.

3. **"O que está exposto na rede agora?"** — vai pra aba **Listening**.
   Mostra todos os "atendentes" que o seu computador tem rodando.
   Crítico antes de plugar em rede pública.

4. **"Tem alguma coisa rodando na porta tal?"** — filtra pelo
   número da porta (ex: "5432") e vê quem está ali.

## O que você vai ver

Duas abas:

| Aba | Pra que serve |
|---|---|
| **Conexões** | Lista todas conexões (saindo e entrando) |
| **Listening** | Lista só "atendentes" (programas esperando conexão) |

E uma barrinha em cima com:
- **Busca**: filtra por nome, IP, porta
- **Auto**: liga/desliga atualização automática (a cada 3s)
- **Atualizar**: força atualização agora
- **Modo admin**: revela conexões de programas do sistema (pede senha)

## O que cada parte faz

### Conexões

Lista todas as conexões. Cada linha mostra:

- **TCP/UDP** com endereço local → endereço de destino
- **Nome do programa** + número de identificação (PID)
- **Estado** colorido:
  - Verde "ESTAB" = conexão ativa, rolando dados
  - Azul "LISTEN" = está esperando alguém chegar
  - Cinza "TIME-WAIT" = acabou de fechar
  - Amarelo "WAIT" / "SYN" = handshake ou esperando peer

A lista atualiza sozinha a cada 3 segundos. Se quiser pausar, desliga
o "Auto".

### Listening

Mostra **só os atendentes** — programas no seu computador esperando
conexão. É a aba mais importante pra **auditoria de segurança**:
qualquer item nessa lista é uma "porta aberta" pra alguém entrar.

Use antes de plugar laptop em rede pública (café, hotel) — quanto
menos coisa aqui, mais protegido você está.

### Modo admin

Normalmente o sistema **esconde** os processos de programas que
rodam como administrador (raiz) — você vê eles como "processo
restrito". Liga o modo admin e ele pede senha pra mostrar tudo.

Cuidado: cada atualização nesse modo pede a senha de novo (não há
"lembrar"). Use pra olhar um momento específico e depois desliga.

## Posso quebrar alguma coisa?

**Não.** Esta ferramenta é **só de leitura** — não muda nada no
sistema, só mostra.

O máximo que pode acontecer: ela usa um pouquinho de CPU pra
ficar atualizando a cada 3 segundos. Se você estiver em outra
aba do Vigia, ela **pausa sozinha** pra não desperdiçar bateria.

## Dica do dia

> Antes de plugar o notebook numa rede pública (aeroporto, café),
> abra a aba **Listening**. Cada item aí é um "atendente" que
> aceita conexão de fora. Quanto **menos** itens, mais seguro.
> Se ver algo que você não reconhece, anota o nome do processo e
> investiga depois. Pra a maioria dos casos: idealmente só
> `cups-browsed` (impressão), `systemd-resolve` (DNS) e talvez um
> `sshd` ou outro programa que você sabe que precisa.
