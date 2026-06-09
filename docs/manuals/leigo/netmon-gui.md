# Monitor de Rede

## Pra que serve

Sabe quando você quer saber **quem está usando a sua internet** naquele
momento? Tipo "será que tem algum programa baixando coisa escondido?".

O **Monitor de Rede** responde exatamente isso, mas pra **dentro do
computador**. Ele mostra, em tempo real e **em português**:

- Quais **aplicativos** estão conversando com sites/serviços na internet
  agora
- **Com quem** eles estão falando (pelo **nome** do site, não só números)
- O que do **seu PC** está **aberto** pra rede (esperando conexões)

É como ter uma janelinha mostrando a "fofoca" da rede do seu computador —
mas organizada por programa e fácil de entender.

## Quando você usa isso

1. **"Quem está usando minha internet?"** — você abre a aba **Conexões** e
   vê, agrupado por aplicativo, quem está conversando com a internet.

2. **"Esse programa está mandando dados pra fora?"** — filtra pelo nome do
   programa (ex: "firefox") e vê com quais sites ele está falando.

3. **"O que do meu PC está exposto na rede?"** — vai pra aba **Escutando**.
   Mostra os "atendentes" que o seu computador deixa abertos. Importante
   antes de plugar em rede pública (café, hotel, aeroporto).

4. **"Tem coisa estranha?"** — procura por um nome de site que você não
   reconhece, ou uma porta que não deveria estar aberta.

## O que você vai ver

Duas abas:

| Aba | Pra que serve |
|---|---|
| **Conexões** | Quem está usando a internet **agora**, agrupado por aplicativo |
| **Escutando** | O que do **seu PC** está aberto pra rede (com explicação de cada porta) |

E uma barrinha em cima com:
- **Busca**: filtra por app, site ou porta (ex: firefox, google, 443)
- **Internas** (só na aba Conexões): liga/desliga as conexões locais
- **Auto**: liga/desliga atualização automática (a cada 3s)
- **Atualizar**: força atualização agora
- **Modo admin**: mostra também os apps do sistema (pede senha)

## O que cada parte faz

### Conexões

Mostra **quem está usando a internet**, **agrupado por aplicativo**. Cada
aplicativo vira uma linha que você pode **abrir** pra ver os detalhes:

- O **nome do app** + quantas conexões ele tem
- Abrindo, cada destino aparece pelo **nome do site** (ex: `google.com`),
  não só pelo número de IP — o programa faz essa tradução sozinho, em
  segundo plano
- O **estado** de cada conexão, em português:
  - **Conectado** (verde) = conversando agora, trocando dados
  - **Escutando** (azul) = esperando alguém chegar
  - **Encerrando** (cinza) = a conexão está fechando
  - **Inativo** / **Conectando** = no meio do caminho

No topo, um **resumo rápido**: *"3 apps na internet · 7 conexões"*.

Por padrão, esta aba mostra **só as conexões com a internet** de verdade.
As **conexões internas** (aquelas em que o computador conversa consigo
mesmo, o tal `127.0.0.1`) ficam **escondidas**, porque normalmente são só
ruído. Se quiser vê-las, ligue o botão **Internas**.

> Os programas que estão **só esperando conexão** (sem estar conversando
> com ninguém) **não aparecem aqui** — eles ficam na aba **Escutando**.

### Escutando

Mostra **o que do seu PC está aberto pra rede** — os "atendentes" que
ficam esperando conexão. É a aba mais importante pra **segurança**: cada
item aqui é uma "porta aberta" por onde alguém poderia tentar entrar.

A grande sacada: cada porta vem com uma **explicação do que ela é**, então
você não precisa decorar números. Por exemplo:

- **Porta 22 — Acesso remoto (SSH)**
- **Porta 631 — Impressão (CUPS)**
- **Porta 5353 — Descoberta de rede (mDNS/Bonjour)**
- **Porta 53 — DNS (resolução de nomes)**

Cada linha também mostra **até onde** aquela porta está aberta:

- **só neste PC (local)** — outros computadores **não** alcançam. Tranquilo.
- **aberta pra qualquer rede** — qualquer um na mesma rede pode tentar
  conectar. Essas ganham um selo **"exposta"** em destaque, pra você
  reparar.

Use esta aba antes de plugar o notebook em rede pública: quanto **menos**
coisa "exposta", mais protegido você está.

### Modo admin

Normalmente o sistema **esconde o nome** dos programas que rodam como
administrador (root, systemd, etc.) — eles aparecem agrupados como
"apps do sistema". Ligue o **Modo admin** e ele pede a senha pra revelar
esses nomes.

Cuidado: nesse modo, **cada atualização pede a senha de novo** (não tem
"lembrar"), e o **Auto** é desligado. Use pra dar uma olhada num momento
específico e depois desligue.

## Posso quebrar alguma coisa?

**Não.** Esta ferramenta é **só de leitura** — não muda nada no sistema,
só mostra.

O máximo que pode acontecer: ela usa um pouquinho de CPU pra ficar
atualizando a cada 3 segundos. Se você trocar pra outra ferramenta do
VigiaOS, ela **pausa sozinha** pra não gastar bateria à toa.

## Dica do dia

> Antes de plugar o notebook numa rede pública (aeroporto, café), abra a
> aba **Escutando** e procure os itens com o selo **"exposta"**. Cada um
> deles aceita conexão de fora. Quanto **menos**, mais seguro. Se ver algo
> que você não reconhece, anote o nome e investigue depois. Para a maioria
> dos casos, o normal é ver pouca coisa exposta — impressão, descoberta de
> rede e, no máximo, um acesso remoto que você mesmo ligou.
