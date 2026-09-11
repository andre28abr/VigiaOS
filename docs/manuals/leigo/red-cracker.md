# Vigia Cracker — robustez de senhas e hashes (para leigos)

## O que é

O **Vigia Cracker** é uma ferramenta de **auditoria defensiva de senhas**. Ele
pega um arquivo de **hashes que você já possui** — por exemplo o `/etc/shadow`
do **seu próprio servidor**, ou hashes exportados de um banco de dados **seu** —
e testa **quais dessas senhas são fracas** o bastante para cair num ataque de
dicionário. O objetivo é um só: **descobrir as senhas fracas para exigir a troca
delas**.

Um "hash" é o embaralhamento matemático de uma senha: o sistema guarda o hash,
não a senha em si. Se uma senha fraca (como `123456` ou `senha2024`) estiver numa
lista comum, o hash dela é facilmente "adivinhado". É exatamente isso que um time
de segurança faz para forçar senhas melhores — e é isso que este módulo faz.

Ele usa duas ferramentas consagradas: o **john** (John the Ripper, roda no
processador, sem configuração) e o **hashcat** (usa a placa de vídeo/GPU, bem
mais rápido).

> **Isto NÃO serve para "descobrir a senha de outra pessoa".** Serve para você
> auditar hashes **que já são seus** e melhorar a segurança do que você
> administra.

## Para que serve

- Auditar as senhas dos usuários do **seu** servidor: quantas são fracas?
- Justificar, com números, uma política de troca de senhas no escritório.
- Conferir se, depois de uma campanha de conscientização, as senhas melhoraram
  (rode de novo e compare).

## Use apenas com autorização

Este módulo só faz sentido sobre **hashes que são seus** ou de um sistema que
você administra com **autorização formal por escrito**. Tentar quebrar senhas de
terceiros sem permissão é **crime no Brasil** (**Lei 12.737/2012** — a "Lei
Carolina Dieckmann"). Ao abrir qualquer módulo do **VigiaRed** pela primeira vez,
você lê e aceita um **termo de uso** que reforça isso. Você é o único responsável
pelo uso.

## Como usar

1. Abra o Vigia Cracker (seção **Red**). Na primeira vez, **aceite o termo de
   uso**.
2. Em *Arquivo de hashes*, aponte o arquivo com os hashes que você quer auditar
   (ex.: uma cópia do `/etc/shadow` do seu servidor).
3. Em *Wordlist*, aponte a **lista de senhas candidatas** — um arquivo de texto
   com uma senha por linha (as famosas "rockyou" e listas de senhas comuns).
4. Escolha o **Tipo de hash**. Se não souber, deixe **Detectar automaticamente
   (john)** — o john tenta adivinhar. Há um catálogo pronto: MD5, SHA-1/256/512,
   NTLM (Windows), bcrypt e os formatos de `/etc/shadow` do Linux
   (md5crypt, sha256crypt, sha512crypt).
5. Escolha a **Ferramenta**: **john** (processador, sem setup) ou **hashcat**
   (placa de vídeo, mais rápido — mas exige escolher o tipo de hash, não tem
   detecção automática).
6. Escolha o **Perfil**:
   - **Dicionário** — testa cada palavra da lista como está. Rápido.
   - **Dicionário + regras** — aplica variações comuns (`Senha` → `S3nh4!`,
     acrescenta ano etc.). Mais completo e mais lento.
7. Clique em iniciar. Durante o teste dá para **cancelar** a qualquer momento.

## Como ler os resultados

No fim, o Vigia Cracker mostra **quantos hashes caíram** — ou seja, **quantas
senhas eram fracas** — sobre o total. Ele mostra o **identificador** de cada hash
fraco (o usuário, ou a posição do hash) para você saber **de quem é a senha que
precisa trocar**.

- Um número alto de senhas fracas é um sinal de alerta: peça a troca imediata
  dessas contas.
- **Zero senhas quebradas é um bom sinal**, mas *não prova* que todas as senhas
  sejam fortes — só que nenhuma estava na lista testada.
- Use **Exportar** para salvar o laudo e anexar a um relatório interno.
- Toda auditoria fica no **Histórico**.

## O que NÃO fazer

- **Não** use este módulo com hashes que **não são seus** e não têm autorização
  escrita.
- **Não** trate "zero senhas quebradas" como "100% seguro": significa apenas que
  a wordlist daquele teste não pegou nenhuma.
- **Não** deixe o arquivo de hashes ou a wordlist em pastas compartilhadas — são
  material sensível.

## Privacidade

O Vigia Cracker roda **inteiramente na sua máquina** — nada é enviado a
servidores da Vigia nem a terceiros. E há um cuidado importante: **o relatório
salvo no histórico NÃO guarda a senha em claro**. Ele guarda apenas o
**identificador** do hash fraco (o "quem"), não a senha descoberta. A senha em si
aparece só na tela e no export TXT, para você agir. Os relatórios ficam com
permissão restrita (**0600** — só você lê), em `~/.local/share/vigia-cracker/`.

## Faz parte do VigiaRed

O Vigia Cracker é a etapa de **Senhas & Hashes** do **VigiaRed**. É um módulo
defensivo por natureza: o resultado não é "invadir", é **uma lista de senhas para
trocar** no que você administra.
