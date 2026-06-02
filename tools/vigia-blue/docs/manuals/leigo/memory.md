# Vigia Memory — perícia na memória do computador (para leigos)

## O que é

Quando um computador está ligado, **tudo o que está acontecendo de verdade** fica
na **memória RAM**: os programas rodando, as conexões abertas, as senhas digitadas,
e até malware que se esconde sem nunca tocar o disco. O **Vigia Memory** faz a
**perícia dessa memória** — como um legista examina o que ficou registrado.

Ele usa o **Volatility 3**, a ferramenta de referência mundial em forense de
memória.

## Como funciona (importante)

O Vigia Memory **analisa um "retrato" da memória** (um *dump*) que foi **capturado
antes**. Ele **não** captura a RAM sozinho — capturar exige uma ferramenta
específica (como o **AVML** ou o **LiME**) e acesso de administrador. Pense assim:
o Vigia Memory é o **legista**; a captura do dump é a **coleta da cena**.

## Para que serve

- Ver **quais programas** estavam rodando num momento (mesmo os escondidos).
- Recuperar o **histórico de comandos** que alguém digitou.
- Ver **conexões de rede** que existiam.
- Encontrar **código injetado** — uma técnica clássica de malware.

## Como usar

1. Tenha um **dump de memória** (arquivo capturado antes).
2. Na aba **Análise**, clique em **Selecionar** e aponte o dump.
3. Escolha um **plugin** (o que você quer ver):
   - **Processos (lista / árvore)** — programas em execução;
   - **Histórico do bash** — comandos digitados;
   - **Conexões de rede** — sockets abertos;
   - **Código injetado (malware)** — sinais de injeção;
   - (e versões para Windows).
4. Clique em **Analisar**. Pode demorar — memória é grande.
5. O resultado vira uma lista. **Clique numa linha** para ver todos os campos
   daquele item (PID, nome, caminho, etc.).

## Privacidade

Roda **100% local**. O dump e a análise ficam só na sua máquina.

## Precisa instalar

O Volatility 3 não vem por padrão. A aba **Sobre** mostra como instalar
(`pipx install volatility3`).
