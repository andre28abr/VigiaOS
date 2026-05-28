# Firewall Manager

## Pra que serve

O **firewall** é como a portaria do seu computador. Toda vez que
algo na internet tenta se conectar com você, ele decide: **deixa
entrar** ou **bloqueia**.

Por padrão, o firewall do seu computador é **bem rigoroso** — quase
nada de fora consegue entrar. E isso é bom, especialmente em redes
desconhecidas (café, aeroporto, hotel).

Esta ferramenta deixa você **ver o firewall e ajustar** quando
precisar abrir uma exceção pontual. Tipo: "deixa esse meu colega
fazer SSH no meu computador hoje à tarde".

## Quando você usa isso

Você raramente precisa abrir essa ferramenta — o firewall padrão do
Fedora já é bom. Mas em 3 situações é útil:

1. **"Quero conferir se o firewall está ligado"** — a aba Status
   mostra "ativo" em verde. Bom de conferir antes de uma reunião
   importante onde você vai compartilhar tela do computador.

2. **"Preciso receber uma conexão"** — exemplos:
   - Compartilhar pasta com colega
   - Receber SSH para alguém te ajudar remoto
   - Rodar um servidor de testes em casa

3. **"Quero trocar o nível de proteção"** — quando muda de rede.
   Em casa, mais relaxado. Em café, mais rígido.

## O que você vai ver

Duas abas principais:

| Aba | Pra que serve |
|---|---|
| **Status** | Mostra se o firewall está ligado, qual zona está usando |
| **Zonas** | Permite abrir/fechar serviços e portas por zona |

## O que cada parte faz

### Status

Logo no topo: "ativo" verde ou "parado" vermelho. Tem um botão pra
ligar/desligar (pede senha).

Embaixo, **Zona padrão** — é o nível de proteção que está sendo
usado. Mais comuns:

- **public** (padrão): bem rigoroso. Use em redes desconhecidas.
- **home**: mais relaxado. Permite alguns serviços internos.
- **internal**: bem aberto. Só em rede 100% confiável (escritório).
- **drop**: bloqueia tudo. Modo paranoia.
- **trusted**: sem firewall na prática. **Cuidado!**

E mostra quais zonas estão ativas (em uso por cada placa de rede).

### Zonas

Aqui você escolhe uma zona no topo e edita o que pode passar:

**Serviços**: lista de aplicativos conhecidos do firewall. Tem nome
amigável (ssh, http, https). Clica no "+" pra adicionar — escolhe
da lista. Clica "Remover" pra tirar — pede confirmação.

**Portas**: se você precisa abrir uma porta específica (ex: 8080
porque seu programa de testes usa essa) e ela não está na lista de
serviços, adiciona aqui. Você digita o número e escolhe se é TCP
ou UDP.

Toda mudança vale na hora E continua valendo depois de reiniciar
o computador.

## Posso quebrar alguma coisa?

**Algumas coisas, sim.** Por isso pede senha.

Riscos:

- **Desligar o firewall** — computador fica sem essa proteção.
  Não faça em rede pública.
- **Mudar zona pra "trusted"** — é praticamente desligar o firewall.
  Use só se sabe muito bem o que está fazendo.
- **Abrir porta sem necessidade** — cada porta aberta é uma porta
  que alguém pode tentar atacar. Abra **só o que precisa, quando
  precisa**.

Coisas que **não** podem dar problema:

- Olhar a aba Status — só leitura
- Listar serviços/portas de uma zona — só leitura
- Cancelar qualquer dialog (clicar Cancelar)

## Dica do dia

> Quando alguém vai te ajudar por SSH, vale a pena: 1) ir na aba
> **Zonas**, escolher a zona ativa (provavelmente `public`),
> 2) clicar "+ Adicionar service" e selecionar **ssh**. Depois do
> trabalho, **remova** o ssh — não deixe permanente. Isso é o
> mesmo princípio de "só abrir a porta da casa quando o entregador
> chegar".
