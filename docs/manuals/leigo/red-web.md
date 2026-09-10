# Vigia Web Scanner — vulnerabilidades de sites (para leigos)

## O que é

O **Vigia Web Scanner** examina uma **aplicação web** (um site ou sistema que
roda no navegador) procurando falhas típicas de aplicação — as do famoso
**OWASP**: **XSS** (injeção de scripts na página), **SQL Injection** (injeção em
banco de dados), inclusão de arquivos, e outras. Ele primeiro **rastreia** o site
(navega pelas páginas e formulários como um robô) e depois **testa** cada ponto
de entrada.

Ele usa o **wapiti**, um scanner de vulnerabilidades web open-source. É uma
varredura **ativa**: o wapiti **envia requisições ao site** (inclusive de teste)
para descobrir como ele reage.

## Para que serve

- Verificar se o **site do escritório** (ou de um cliente que autorizou) tem
  falhas de aplicação conhecidas antes que um invasor as encontre.
- Conferir se uma correção fechou uma falha (rodar de novo depois de ajustar).
- Complementar o **Vuln Scanner**: aquele olha o servidor e serviços; este olha
  a **lógica da aplicação** (formulários, parâmetros, páginas).

## Use apenas com autorização

Este módulo faz **varredura ativa** e chega a **enviar dados de teste** ao site.
Só use contra:

- **sites/aplicações seus**; ou
- alvos com **autorização formal por escrito**.

Testar um site de terceiros sem permissão é **crime no Brasil**
(**Lei 12.737/2012** — a "Lei Carolina Dieckmann"). Ao abrir qualquer módulo do
**VigiaRed** pela primeira vez, você lê e aceita um **termo de uso** que reforça
isso. Você é o único responsável pelo uso.

> Cuidado extra: como o Web Scanner envia dados de teste, evite rodá-lo contra um
> site em produção com dados reais sem entender o impacto. Prefira um ambiente de
> homologação/laboratório.

## Como usar

1. Abra o Vigia Web Scanner (seção **Red**). Na primeira vez, **aceite o termo de
   uso**.
2. Na aba **Varredura**, em *Alvo autorizado*, digite a **URL** — ex.:
   `https://exemplo.com.br`. (Se você digitar só o domínio, ele coloca `http://`
   na frente.)
3. Escolha o **Escopo** (perfil), que decide **até onde** o robô navega:
   - **Rápida** — só a **página** informada; rápido.
   - **Padrão** (recomendado) — a **pasta** da URL (o mesmo diretório).
   - **Completa** — o **domínio inteiro**; bem mais lento e intrusivo.
4. Clique em **Escanear**. Durante a varredura o botão vira **Cancelar** — pode
   parar quando quiser.

## Como ler os resultados

Os achados aparecem na aba **Achados**, **ordenados por gravidade**. Cada um
mostra a **categoria** da falha (ex.: *Cross Site Scripting*, *SQL Injection*), a
**severidade**, **onde** foi encontrada (método e caminho) e uma **descrição**.

- Achados **críticos/altos** merecem atenção imediata — geralmente indicam uma
  falha explorável na aplicação.
- Nem todo achado é urgente: leia a descrição e a severidade para priorizar.
- Use **Exportar** para salvar o laudo.
- Toda varredura fica na aba **Histórico**.

> Um achado é um **indício** para revisão por um humano — não uma prova de que o
> site já foi invadido.

## O que NÃO fazer

- **Não** rode contra sites que não são seus e não têm autorização escrita.
- **Não** use a varredura **Completa** contra um site grande de produção "só para
  ver" — ela navega o domínio inteiro e envia muitos testes.
- **Não** explore em terceiros as falhas encontradas — o propósito é **corrigir**
  o que é seu.

## Privacidade

O Web Scanner roda **na sua máquina**. As requisições vão **só para o site que
você digitou**; nada é enviado a servidores da Vigia. Cada varredura é salva
localmente com permissão restrita (**0600** — só você lê), em
`~/.local/share/vigia-web/`.

## Faz parte do VigiaRed

O Vigia Web Scanner completa o "tripé" de varredura do **VigiaRed** no nível da
**aplicação web**, ao lado do **Network Scanner** (portas/serviços) e do **Vuln
Scanner** (vulnerabilidades por templates).
