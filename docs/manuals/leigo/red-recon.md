# Vigia Recon — reconhecimento passivo / OSINT (para leigos)

## O que é

O **Vigia Recon** monta o "mapa externo" de um domínio a partir de
**informações que já são públicas** — sem tocar nos servidores do alvo. A
partir do domínio (ex.: `exemplo.com.br`) ele descobre **e-mails**,
**subdomínios**, **endereços IP** e **URLs de interesse** que estão espalhados
por registros públicos.

Ele usa o **theHarvester**, uma ferramenta consagrada de **OSINT** (*Open Source
Intelligence* — inteligência de fontes abertas). O Recon é **passivo**: ele só
**lê** o que buscadores, bases de certificado e serviços de DNS já publicam. Ele
**não** envia pacotes ao site do alvo, **não** tenta entrar em nada e **não**
"ataca". É o mesmo que juntar informação que qualquer pessoa acharia no Google —
só que organizado num só lugar.

## Para que serve

- Ver **qual é a superfície externa** de um domínio seu (ou de um cliente que
  autorizou por escrito): quantos subdomínios existem, quais e-mails aparecem
  publicamente, quais IPs estão associados.
- **Preparar uma auditoria autorizada**: saber o que está exposto antes de olhar
  cada peça com mais cuidado.
- **Higiene digital do escritório**: descobrir e-mails ou serviços antigos que
  ficaram públicos e talvez devessem ser desativados.

## Use apenas com autorização

O Vigia Recon faz parte do **VigiaRed**, a seção de pentest educacional. Na
primeira vez que você abre qualquer módulo do Red, aparece um **termo de uso**
que você precisa ler e aceitar. Ele diz, em resumo:

> Use somente contra **sistemas próprios** ou com **autorização formal por
> escrito**. Acesso não autorizado a dispositivos é crime no Brasil
> (**Lei 12.737/2012** — a "Lei Carolina Dieckmann").

Mesmo sendo passivo, o Recon é uma ferramenta de reconhecimento. **Investigue só
domínios que são seus ou que você tem permissão explícita para investigar.** Não
use para bisbilhotar terceiros. Você é o único responsável pelo uso.

## Como usar

1. Abra o Vigia Recon (seção **Red** do VigiaOS). Na primeira vez, **leia e
   aceite o termo de uso**.
2. Na aba **Investigar**, digite **apenas o domínio** no campo *Domínio do
   alvo* — ex.: `exemplo.com.br`. Não precisa de `http://`, nem de caminho, nem
   de e-mail; se você colar algo assim, ele limpa sozinho.
3. Clique em **Investigar**. A busca consulta várias fontes públicas e pode
   levar **1 a 2 minutos** — é normal.
4. Veja os **resultados**, agrupados em quatro categorias clicáveis:
   - **E-mails** — endereços que aparecem publicamente ligados ao domínio.
   - **Subdomínios** — outros nomes sob o domínio (ex.: `mail.exemplo.com.br`).
   - **Endereços IP** — IPs associados.
   - **URLs de interesse** — endereços de páginas encontradas.
   - **Clique** numa categoria para abri-la e ver a lista.
5. Nos **Endereços IP**, cada linha tem um botão **Escanear**: ele **envia**
   aquele IP para o **Vigia Network Scanner** (o próximo módulo). Depois é só
   abrir o Network Scanner, que já vem com o IP preenchido.

## Como ler os resultados

- **Nenhum dado encontrado** não quer dizer que o domínio "é seguro" — só que as
  fontes públicas não retornaram nada desta vez. Confira se você digitou a raiz
  do domínio (ex.: `nmap.com`, não `www.nmap.com/algo`).
- Um e-mail ou subdomínio na lista **não é um problema por si só** — é apenas
  "o que está público". Serve para você decidir o que revisar.
- Toda investigação fica salva na aba **Histórico**, com data e quantidade de
  achados. Clique numa linha para abrir o relatório completo.

## O que NÃO fazer

- **Não** use o Recon contra domínios de terceiros sem autorização por escrito.
- **Não** trate os e-mails encontrados como uma lista para enviar spam ou fazer
  phishing — isso é ilegal e foge totalmente do propósito educacional.
- **Não** ache que o resultado é uma lista completa: é o que as fontes públicas
  conheciam no momento, nada mais.

## Privacidade

O Vigia Recon roda **na sua máquina**. As **únicas** coisas que saem do seu
computador são as **consultas** que o theHarvester faz às fontes públicas (o
mesmo que uma busca na internet). **Nenhum relatório é enviado** para lugar
nenhum. Cada investigação é salva localmente com permissão restrita (**0600** —
só você lê), em `~/.local/share/vigia-recon/`.

## Faz parte do VigiaRed

O Vigia Recon é o **primeiro passo** (reconhecimento passivo) do **VigiaRed**, a
suíte de pentest educacional do ecossistema Vigia. O passo seguinte, quando você
quiser olhar um host de perto, é o **Vigia Network Scanner** (que já é ativo — e
por isso exige ainda mais cuidado com autorização).
