# Vigia Memory — perícia na memória do computador (para leigos)

## O que é

Quando um computador está ligado, **tudo o que está acontecendo de verdade** fica
na **memória RAM**: os programas rodando, as conexões abertas, as senhas digitadas,
e até malware que se esconde sem nunca tocar o disco. O **Vigia Memory** faz a
**perícia dessa memória** — como um legista examina o que ficou registrado.

Ele usa o **Volatility 3**, a ferramenta de referência mundial em forense de
memória.

## Como funciona (importante)

O Vigia Memory trabalha com um **"retrato" da memória** (um *dump*). Você tem
**duas opções**:

1. **Capturar agora, no próprio programa** — o botão **Capturar** tira o retrato
   da RAM *desta* máquina na hora (usa o **AVML** e pede a senha de admin). O
   arquivo vai pra `~/teste/memory/` e já fica pronto pra analisar.
2. **Abrir um dump que você já tem** — de um servidor, de outra máquina: é só
   apontar o arquivo.

Pense assim: o Vigia Memory é o **legista** — e agora ele também faz a **coleta
da cena** (a captura) desta máquina.

## Para que serve

- Ver **quais programas** estavam rodando num momento (mesmo os escondidos).
- Recuperar o **histórico de comandos** que alguém digitou.
- Ver **conexões de rede** que existiam.
- Encontrar **código injetado** — uma técnica clássica de malware.

## Como usar

1. Na aba **Análise**, obtenha o dump de um jeito:
   - **Capturar** → tira o retrato da RAM desta máquina agora (pede senha de
     admin); **ou**
   - **Selecionar** → aponta um dump que você já tem.
2. Escolha um **plugin** (o que você quer ver):
   - **Processos (lista / árvore)** — programas em execução;
   - **Histórico do bash** — comandos digitados;
   - **Conexões de rede** — sockets abertos;
   - **Código injetado (malware)** — sinais de injeção;
   - (e versões para Windows).
3. Clique em **Analisar**. Pode demorar — memória é grande.
4. O resultado vira uma lista. **Clique numa linha** para ver todos os campos
   daquele item (PID, nome, caminho, etc.).

## Privacidade

Roda **100% local**. O dump e a análise ficam só na sua máquina.

## Uma pegadinha (dumps de Linux)

Pra analisar um dump **de Linux**, o Volatility também precisa de um "mapa" do
kernel (os *símbolos*). Quando falta, a análise mostra um botão **Preparar
símbolos**: o Vigia tenta **gerar** esse mapa sozinho — e, se não der (no
Silverblue costuma faltar o `kernel-debuginfo`), ele te mostra o **passo a passo
copiável** pro seu kernel exato (com toolbox). No **Windows** isso é automático.

## Precisa instalar

- **Volatility 3** (a análise) — `pipx install volatility3`.
- **AVML** (a captura) — vem com `./install/blue-deps.sh` (baixa o binário
  oficial da Microsoft). Sem ele, o botão **Capturar** fica desligado, mas
  abrir e analisar dumps existentes funciona normal.

A aba **Sobre** do módulo mostra os detalhes.
