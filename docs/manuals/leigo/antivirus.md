# Antivírus

## Pra que serve

Pra **procurar vírus em arquivos** do seu computador.

Usa o **ClamAV**, um antivírus de código aberto reconhecido. Funciona
diferente do Norton ou Kaspersky do Windows: não fica rodando o tempo
todo bisbilhotando tudo. Você **manda escanear** quando quiser — uma
pasta, um arquivo, sua pasta de Downloads.

É útil principalmente em **2 cenários**:

1. **Você baixou um arquivo e vai mandar pra alguém usando Windows.**
   Mesmo que o vírus não afete seu Linux, você não quer passar
   adiante.
2. **Escritório LGPD.** Você precisa **provar** que está cuidando dos
   dados dos clientes. Escanear periodicamente é parte da diligência.

## Quando você usa isso

- **Depois de baixar arquivos da internet** — especialmente PDFs,
  documentos do Office, executáveis.
- **Antes de mandar arquivos por email** pra clientes ou parceiros.
- **Periodicamente** (1x/semana) na sua pasta de Downloads ou
  Documents — preventivo.
- **Quando alguém te mandar um arquivo suspeito** — antes de abrir.
- **Servidor que recebe arquivos de terceiros** — scan diário via cron.

## O que você vai ver

São **3 abas**:

1. **Scan** — Onde você escolhe o que escanear e vê o resultado:
   - Caixa de texto pra digitar um caminho (ou clicar a pasta)
   - **4 atalhos**: Home, Downloads, Documents, /tmp
   - Botão **Iniciar scan**
   - Conforme escaneia, vai mostrando os arquivos analisados
   - Se achar vírus, aparece em destaque **vermelho**

2. **Base de dados** — A "lista de vírus conhecidos":
   - Versão do ClamAV
   - Idade da base (quanto tempo desde a última atualização)
   - Botão **Atualizar base agora** (pede senha admin)
   - Lista dos últimos scans feitos

3. **Sobre** — Manual interno mais detalhado.

## O que cada parte faz

- **Banner no topo** — avisa se a base está desatualizada ou se o
  ClamAV não está instalado.
- **Caminho do scan** — onde você diz "olha aqui dentro". Pode ser
  uma pasta inteira ou um arquivo só.
- **Atalhos (Home, Downloads...)** — os lugares mais comuns onde
  baixamos arquivo do mundo externo.
- **Iniciar scan** — começa a varredura. Vai aparecendo log conforme
  ele encontra arquivos.
- **Parar** — cancela o scan se demorar demais.
- **Atualizar base** — baixa as assinaturas mais recentes de vírus
  (cerca de 250 MB, leva 30-90 segundos).
- **Histórico** — guarda registro JSON de cada scan no
  `~/.local/share/vigia-antivirus/` com permissão **só você pode
  ler**. Útil pra audit LGPD.

## Posso quebrar alguma coisa?

**Não com o scan.** O scan é somente leitura — ele só **olha** os
arquivos, não apaga nem move nada.

**Com a atualização da base, também não.** Ela só baixa um arquivo
novo de assinaturas.

**Atenção:** se aparecer um arquivo como **vírus encontrado**, e
você decidir **apagar manualmente**, aí sim você pode deletar algo
importante por engano. Sempre confirme antes de deletar:

1. O ClamAV às vezes dá **falso positivo** (acusa arquivo limpo como
   vírus).
2. Olhe o nome do arquivo. Se for algo que você reconhece (foto da
   família, doc do escritório), pesquise o nome da assinatura no
   Google antes de deletar.
3. Em caso de dúvida, **mova pra outra pasta** em vez de deletar.

## Dica do dia

**Atualize a base 1x/semana, no mínimo.** Se ela está desatualizada
há mais de 30 dias, o scan **não pega vírus novos**.

A maneira mais fácil:

1. Abra o Vigia Antivírus
2. Vai na aba **Base de dados**
3. Olha a "Idade da base"
4. Se passou de 7 dias, clica em **Atualizar base agora**
5. Digita a senha
6. Espera 30-90 segundos

Você também pode automatizar isso via `systemd timer` ou cron — pergunte
a alguém que entenda. Mas pra escritório pequeno, atualização manual 1x/semana
já resolve.

**Importante**: o ClamAV detecta principalmente **malware Windows**
(arquivos .exe, .dll, documentos Office com macros maliciosas) e
**alguns shell scripts conhecidos**. **Não pega** ataques sofisticados
ou zero-day. É uma camada de baseline — combine com outras (firewall,
hardening, rootkit scanner).
