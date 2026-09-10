# Vigia Network Scanner — portas e serviços (para leigos)

## O que é

O **Vigia Network Scanner** olha um computador (ou uma faixa de rede) e descobre
**quais "portas" estão abertas** e **que serviço** responde em cada uma — por
exemplo: "a porta 22 está aberta e é um servidor SSH versão X", "a porta 443 é um
site Apache". Portas são como as portas de um prédio: cada serviço de rede
(site, e-mail, banco de dados) atende numa porta.

Ele usa o **nmap**, a ferramenta de varredura de rede mais conhecida do mundo.
Diferente do **Vigia Recon** (que é passivo, só lê fontes públicas), o Network
Scanner é **ativo**: ele **conversa com o alvo**, mandando pacotes de rede para
descobrir o que está respondendo. Por isso ele exige ainda mais cuidado com
autorização.

## Para que serve

- Saber **o que está exposto** num servidor seu: quais portas estão abertas,
  quais serviços/versões respondem.
- Conferir se um serviço que você achava **fechado** não está, por engano,
  aberto para a rede.
- **Inventariar a rede local** do escritório: quais máquinas estão vivas
  (descoberta de hosts).
- Aprofundar um IP que o **Vigia Recon** encontrou (o botão "Escanear" do Recon
  já traz o IP para cá).

## Use apenas com autorização

Este módulo faz **varredura ativa** — ele toca no alvo. Só use em:

- **sistemas seus** (seu servidor, sua rede, um laboratório de estudo); ou
- alvos com **autorização formal por escrito**.

Escanear máquinas de terceiros sem permissão é **crime no Brasil**
(**Lei 12.737/2012** — a "Lei Carolina Dieckmann"). Ao abrir qualquer módulo do
**VigiaRed** pela primeira vez, você lê e aceita um **termo de uso** que reforça
isso. Você é o único responsável pelo uso.

## Como usar

1. Abra o Vigia Network Scanner (seção **Red**). Na primeira vez, **aceite o
   termo de uso**.
2. Na aba **Varredura**, em *Alvo autorizado*, digite um **domínio**, **IP** ou
   **faixa** — ex.: `192.168.0.10`, `exemplo.com.br`, `192.168.0.0/24` ou
   `192.168.0-255.1`.
3. Escolha a **Profundidade** (perfil). Os principais:
   - **Top serviços** — as 20 portas mais comuns; relâmpago.
   - **Rápida** — as 100 portas mais comuns.
   - **Padrão** (recomendado) — 1000 portas + detecção de serviço/versão.
   - **Web** — portas típicas de site (80, 443, 8080…).
   - **Completa** — todas as 65535 portas; leva minutos.
   - **Descoberta de hosts** — só descobre quem está vivo numa faixa, sem varrer
     portas.
   - Perfis marcados **"admin"** (Furtiva/SYN, UDP, Agressiva) precisam do **Modo
     admin** (veja abaixo).
4. (Opcional) Em *Portas*, você pode digitar portas específicas — ex.:
   `80,443,8000-8100`.
5. (Opcional) Em *Scripts NSE*, escolha um conjunto extra de checagens:
   **Padrão (seguros)**, **Web** ou **Vulnerabilidades** (procura falhas
   conhecidas; mais lento e intrusivo).
6. Clique em **Escanear**. Durante a varredura o botão vira **Cancelar** — pode
   parar a qualquer momento.
7. Se quiser guardar o perfil atual como o seu padrão, o módulo lembra suas
   opções para a próxima vez.

## Modo admin (com senha)

Algumas técnicas (SYN, UDP e **detecção de Sistema Operacional**) precisam de
privilégio de administrador. Ligue o **Modo admin** e o VigiaOS pedirá sua senha
por uma **janelinha do sistema** (Polkit/pkexec) — nunca por linha de comando às
cegas. Sem o Modo admin, o Scanner usa uma técnica que funciona **sem senha**
(TCP connect) e continua útil.

## Como ler os resultados

Para cada host encontrado aparece: o **endereço** (e nome, se houver), o
**Sistema Operacional** detectado (quando disponível) e a lista de **portas
abertas** com o serviço/versão de cada uma. Se você usou scripts NSE de
vulnerabilidade, os achados aparecem indentados sob a porta.

- Uma **porta aberta não é, sozinha, um problema** — é um serviço respondendo.
  O que importa é *se aquele serviço deveria estar exposto* e *se a versão está
  atualizada*.
- Use o botão **Exportar** para salvar o resultado em **TXT** ou **XML** (útil
  para anexar a um laudo).
- Toda varredura fica na aba **Histórico**.

## O que NÃO fazer

- **Não** escaneie IPs ou redes que não são seus e não têm autorização escrita.
- **Não** rode a varredura **Completa** ou **UDP** contra uma faixa grande "só
  para ver" — é lento, barulhento na rede e pode disparar alarmes. Comece pelo
  perfil **Padrão**.
- **Não** interprete "porta aberta" como "invadido": é apenas o mapa do que está
  ouvindo.

## Privacidade

O Network Scanner roda **na sua máquina**. Os pacotes de varredura vão **só para
o alvo que você digitou** — nada é enviado a servidores da Vigia nem a terceiros.
Cada varredura é salva localmente com permissão restrita (**0600** — só você lê),
em `~/.local/share/vigia-netscan/`.

## Faz parte do VigiaRed

O Vigia Network Scanner é o passo **ativo** do **VigiaRed**, logo depois do
reconhecimento passivo (Vigia Recon). O que ele encontrar pode ser aprofundado
pelo **Vigia Vuln Scanner** (vulnerabilidades por templates).
