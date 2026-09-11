# Vigia Wireless — a senha do SEU Wi-Fi aguenta? (para leigos)

## O que é

O **Vigia Wireless** responde a uma pergunta simples sobre a **sua própria rede
sem fio**: *"a senha do meu Wi-Fi aguenta um ataque de dicionário?"* Ele testa se
a senha do **seu** ponto de acesso é fraca o suficiente para ser adivinhada a
partir de uma lista de senhas comuns.

Ele usa a suíte **aircrack-ng**, referência mundial em auditoria de Wi-Fi. A
auditoria acontece em **dois passos**:

1. **Capturar o handshake** — o "aperto de mão" de 4 vias que acontece quando um
   aparelho se conecta ao Wi-Fi. Esse passo é feito **fora do app**, porque exige
   uma placa em **modo monitor** e privilégio de administrador (root). O manual
   explica os comandos.
2. **Testar o handshake** contra uma lista de senhas — este é o passo que **o app
   faz**. Ele só precisa do arquivo de captura (`.cap`) e de uma wordlist; **não
   toca em nenhuma rede**.

> **Só na SUA rede.** Este módulo é para você medir a força da sua própria senha
> de Wi-Fi. Acessar rede de terceiros sem autorização é **crime** (veja abaixo).

## Para que serve

- Saber se a senha do Wi-Fi do escritório é fraca e precisa ser trocada.
- Comprovar, para a sua equipe, por que uma senha longa e única é importante.
- Reconferir depois de trocar a senha (o handshake antigo não vale mais).

## Use apenas na sua própria rede

Este módulo é **só para a rede que é sua** ou para a qual você tem **autorização
formal por escrito**. Capturar handshake ou tentar a senha de uma rede alheia é
**crime no Brasil** (**Lei 12.737/2012** — a "Lei Carolina Dieckmann"). Ao abrir
qualquer módulo do **VigiaRed** pela primeira vez, você lê e aceita um **termo de
uso** que reforça isso. Você é o único responsável pelo uso.

## Passo 1 — capturar o handshake (fora do app)

Este passo roda no terminal, com a placa em modo monitor e como administrador. É
feito **só na sua rede**. Em resumo:

1. Coloque a placa em modo monitor e descubra o **canal** e o **BSSID** (o
   endereço da sua rede, no formato `AA:BB:CC:DD:EE:FF`).
2. Grave o tráfego travando na sua rede, com o **airodump-ng**:
   `airodump-ng --bssid <SEU_BSSID> --channel <CANAL> -w minha-rede <interface>`
   — o `--bssid` e o `--channel` **travam a captura no seu ponto de acesso**, sem
   varrer o espectro inteiro.
3. Espere um aparelho seu conectar. Para acelerar, você pode forçar uma
   reconexão de um dispositivo **seu** com o **aireplay-ng**:
   `aireplay-ng --deauth 3 -a <SEU_BSSID> <interface>` — isso derruba a conexão
   por instantes, então use **apenas na sua rede**.
4. Quando o airodump indicar *"WPA handshake"*, você tem o arquivo `.cap`.

O app **monta esses comandos** para você e a aba **Sobre** os documenta — mas a
captura em si acontece fora dele.

## Passo 2 — testar o handshake (o app faz)

1. Abra o Vigia Wireless (seção **Red**). Na primeira vez, **aceite o termo de
   uso**.
2. Em *Captura*, aponte o arquivo `.cap`/`.pcap` do **passo 1**.
3. Em *Wordlist*, aponte a lista de senhas candidatas.
4. (Opcional) Informe o **BSSID** da sua rede, para focar o teste.
5. Clique em iniciar. Dá para **cancelar** a qualquer momento.

## Como ler os resultados

- Se a senha estiver na lista, o app mostra **"senha FRACA — caiu no dicionário"**
  e exibe a senha na tela: **troque-a imediatamente** por uma frase longa e única.
- Se **não** cair, o resultado é **"a senha NÃO caiu no dicionário testado"**: um
  bom sinal — mas *não prova* que seja inquebrável.
- Se a captura não tiver um handshake válido, o app avisa para refazer o passo 1.
- Use **Exportar** para salvar o laudo; o **Histórico** guarda cada auditoria.

## O que NÃO fazer

- **Não** capture nem teste redes que **não são suas** e não têm autorização
  escrita.
- **Não** use o aireplay-ng contra dispositivos de terceiros — ele derruba
  conexões.
- **Não** trate "não caiu" como garantia absoluta de segurança.

## Privacidade

O teste roda **na sua máquina** e não fala com rede nenhuma — só lê o arquivo
`.cap`. Nada é enviado a servidores da Vigia. E há um cuidado importante: **o
histórico NÃO guarda a senha em claro** — registra apenas *que* a senha era fraca.
A senha aparece só na tela e no export TXT, para você agir. Os relatórios ficam
com permissão restrita (**0600** — só você lê), em `~/.local/share/vigia-wireless/`.

## Faz parte do VigiaRed

O Vigia Wireless é o módulo de **Wireless** do **VigiaRed**. Como o Vigia Cracker,
é defensivo por natureza: o resultado não é "invadir", é **saber se a sua senha de
Wi-Fi precisa ser trocada**.
