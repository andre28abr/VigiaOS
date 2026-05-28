# SELinux Manager

## Pra que serve

O **SELinux** é como um segurança rigoroso que mora dentro do
computador. Ele observa cada programa e decide o que aquele programa
**tem permissão** de fazer — mesmo que você (o dono) tenha autorizado
um administrador.

Por exemplo: o navegador pode mexer nos seus arquivos pessoais, mas
**não** pode mexer no sistema. O servidor de impressão pode usar a
impressora, mas **não** pode acessar sua câmera. E assim por diante.

Esta ferramenta deixa você **ver** e **ajustar** esse segurança
interno. Tudo numa janela amigável, em português.

## Quando você usa isso

Você raramente precisa abrir essa ferramenta — o SELinux funciona
sozinho. Mas existem 3 situações comuns:

1. **"Um programa parou de funcionar do nada"** — pode ser o SELinux
   bloqueando. A aba **Bloqueios (Denials)** mostra o que foi
   bloqueado nas últimas horas.

2. **"Movi arquivos de lugar e o site/serviço quebrou"** — quando
   você arrasta arquivos para uma pasta protegida, eles perdem a
   "etiqueta" certa e o programa que os usa para de enxergar. A aba
   **Arquivos** conserta isso com 1 clique.

3. **"Preciso que um programa específico faça algo a mais"** — a aba
   **Switches (Booleans)** tem ~300 chavinhas que liberam permissões
   pontuais (ex: "permitir que o servidor web acesse a internet").

## O que você vai ver

Logo no topo, **6 abas** com nomes claros:

| Aba | Pra que serve |
|---|---|
| **Status** | Mostra se o SELinux está ligado (Enforcing) ou desligado |
| **Booleans** | ~300 chavinhas para liberar permissões pontuais |
| **Bloqueios** | Lista o que o SELinux bloqueou recentemente |
| **Arquivos** | Conserta arquivos com etiqueta errada |
| **Rede** | Lista quais portas pertencem a quais serviços |
| **Processos** | Mostra cada programa rodando e seu "contexto" |

## O que cada parte faz

### Status

Tem 3 modos possíveis e a aba mostra qual está ativo:

- **Enforcing** (recomendado): o segurança bloqueia o que não é
  permitido. É o padrão e está em verde.
- **Permissive**: o segurança só **avisa** mas não bloqueia. Útil
  para descobrir o que ele bloquearia (debug).
- **Disabled**: o segurança está desligado. **Não recomendado** —
  fica em vermelho com aviso.

Tem um switch grande pra trocar entre Enforcing e Permissive na hora.
E um combo pra trocar o modo que vai valer no próximo boot.

### Booleans (switches)

Pense em ~300 chavinhas, cada uma libera uma permissão específica.
Ex: `httpd_can_network_connect` liga = "deixa o servidor web fazer
conexões para outros sites". A busca no topo filtra por nome ou
descrição em português.

### Bloqueios (Denials)

Você escolhe um período (hoje, esta semana, recente) e clica
"Carregar". Aparece a lista do que o SELinux bloqueou. Pra cada
bloqueio, tem um botão **Gerar** que sugere uma regrinha para
desbloquear aquele caso.

### Arquivos

Você digita uma pasta (ex: `/var/www`) e clica "Restaurar contextos".
A ferramenta restaura as etiquetas do SELinux nessa pasta.
**Resolve 90% dos casos** de "movi arquivo e parou de funcionar".

### Rede e Processos

São de leitura — mostram informação técnica útil pra entender o que
o SELinux está fazendo. Útil pra quem quer aprender ou auditar.

## Posso quebrar alguma coisa?

**Algumas coisas, sim.** Por isso a ferramenta pede senha de
administrador antes de fazer mudanças importantes.

Riscos:

- **Desligar o SELinux (Disabled)** — sistema fica sem essa camada
  de proteção. Só faça se um técnico te orientou.
- **Mudar booleans** — pode ligar uma permissão que abre uma porta
  pra atacante. Leia a descrição em português antes.
- **restorecon em pasta errada** — se você digitar `/` (raiz), pode
  levar muito tempo. Mas não quebra nada permanentemente.

Coisas que **não** podem dar problema:

- Olhar as abas Status, Bloqueios, Rede, Processos — só leitura
- Pesquisar booleans (até clicar no switch)

## Dica do dia

> Se um serviço parou de funcionar de repente, **antes de mexer em
> qualquer coisa**, abra a aba **Bloqueios**, escolha "Recente (10
> min)" e clique Carregar. Se aparecer algo do seu serviço, foi o
> SELinux. Clique **Gerar** ao lado pra ver o que ele bloqueou — e
> peça a solução para alguém técnico (ou aplique a sugestão se você
> for o técnico).
