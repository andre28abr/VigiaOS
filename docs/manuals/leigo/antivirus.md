# Antivirus

## Pra que serve

Pra **procurar virus em arquivos** do seu computador.

Usa o **ClamAV**, um antivirus de codigo aberto reconhecido. Funciona
diferente do Norton ou Kaspersky do Windows: nao fica rodando o tempo
todo bisbilhotando tudo. Voce **manda escanear** quando quiser — uma
pasta, um arquivo, sua pasta de Downloads.

E util principalmente em **2 cenarios**:

1. **Voce baixou um arquivo e vai mandar pra alguem usando Windows.**
   Mesmo que o virus nao afete seu Linux, voce nao quer passar
   adiante.
2. **Escritorio LGPD.** Voce precisa **provar** que esta cuidando dos
   dados dos clientes. Escanear periodicamente e parte da diligencia.

## Quando voce usa isso

- **Depois de baixar arquivos da internet** — especialmente PDFs,
  documentos do Office, executaveis.
- **Antes de mandar arquivos por email** pra clientes ou parceiros.
- **Periodicamente** (1x/semana) na sua pasta de Downloads ou
  Documents — preventivo.
- **Quando alguem te mandar um arquivo suspeito** — antes de abrir.
- **Servidor que recebe arquivos de terceiros** — scan diario via cron.

## O que voce vai ver

Sao **3 abas**:

1. **Scan** — Onde voce escolhe o que escanear e ve o resultado:
   - Caixa de texto pra digitar um caminho (ou clicar a pasta)
   - **4 atalhos**: Home, Downloads, Documents, /tmp
   - Botao **Iniciar scan**
   - Conforme escaneia, vai mostrando os arquivos analisados
   - Se achar virus, aparece em destaque **vermelho**

2. **Base de dados** — A "lista de virus conhecidos":
   - Versao do ClamAV
   - Idade da base (quanto tempo desde a ultima atualizacao)
   - Botao **Atualizar base agora** (pede senha admin)
   - Lista dos ultimos scans feitos

3. **Sobre** — Manual interno mais detalhado.

## O que cada parte faz

- **Banner no topo** — avisa se a base esta desatualizada ou se o
  ClamAV nao esta instalado.
- **Caminho do scan** — onde voce diz "olha aqui dentro". Pode ser
  uma pasta inteira ou um arquivo soh.
- **Atalhos (Home, Downloads...)** — os lugares mais comuns onde
  baixamos arquivo do mundo externo.
- **Iniciar scan** — comeca a varredura. Vai aparecendo log conforme
  ele encontra arquivos.
- **Parar** — cancela o scan se demorar demais.
- **Atualizar base** — baixa as assinaturas mais recentes de virus
  (cerca de 250 MB, leva 30-90 segundos).
- **Historico** — guarda registro JSON de cada scan no
  `~/.local/share/vigia-antivirus/` com permissao **so voce pode
  ler**. Util pra audit LGPD.

## Posso quebrar alguma coisa?

**Nao com o scan.** O scan e somente leitura — ele soh **olha** os
arquivos, nao apaga nem move nada.

**Com a atualizacao da base, tambem nao.** Ela soh baixa um arquivo
novo de assinaturas.

**Atencao:** se aparecer um arquivo como **virus encontrado**, e
voce decidir **apagar manualmente**, ai sim voce pode deletar algo
importante por engano. Sempre confirme antes de deletar:

1. O ClamAV as vezes da **falso positivo** (acusa arquivo limpo como
   virus).
2. Olhe o nome do arquivo. Se for algo que voce reconhece (foto da
   familia, doc do escritorio), pesquise o nome da assinatura no
   Google antes de deletar.
3. Em caso de duvida, **mova pra outra pasta** em vez de deletar.

## Dica do dia

**Atualize a base 1x/semana, no minimo.** Se ela esta desatualizada
ha mais de 30 dias, o scan **nao pega virus novos**.

A maneira mais facil:

1. Abra o Vigia Antivirus
2. Vai na aba **Base de dados**
3. Olha a "Idade da base"
4. Se passou de 7 dias, clica em **Atualizar base agora**
5. Digita a senha
6. Espera 30-90 segundos

Voce tambem pode automatizar isso via `systemd timer` ou cron — pergunte
a alguem que entenda. Mas pra escritorio pequeno, atualizacao manual 1x/semana
ja resolve.

**Importante**: o ClamAV detecta principalmente **malware Windows**
(arquivos .exe, .dll, documentos Office com macros maliciosas) e
**alguns shell scripts conhecidos**. **Nao pega** ataques sofisticados
ou zero-day. E uma camada de baseline — combine com outras (firewall,
hardening, rootkit scanner).
