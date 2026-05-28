# Verificador de Rootkit

## Pra que serve

Pra **descobrir se tem alguem espionando seu computador escondido**.

Um **rootkit** e um tipo de malware muito perigoso porque ele se
**esconde** do sistema. Voce nao ve o processo dele, nao ve os
arquivos dele. Ele pode estar la ha meses, lendo seus emails,
capturando senhas, mandando seus dados pra fora — e voce nao percebe.

Este Verificador roda **dois programas classicos** que sabem procurar
sinais de rootkit:

- **chkrootkit** — rapido (~30 segundos)
- **Rootkit Hunter** (rkhunter) — completo (2 a 5 minutos, 200+ checagens)

Sao complementares: rode os dois pra ter cobertura cruzada.

## Quando voce usa isso

- **Quando o computador esta agindo estranho** sem motivo aparente:
  lento, fan trabalhando, conexoes de rede inexplicaveis.
- **Periodicamente** (1x/mes) como audit baseline.
- **Depois de uma atualizacao grande** do sistema.
- **Apos compartilhar o computador** com alguem desconhecido.
- **Em servidor** que ficou exposto a internet, mesmo brevemente.
- **Audit LGPD** — comprovar que voce verifica integridade
  periodicamente.

## O que voce vai ver

Sao **4 abas**:

1. **chkrootkit** — Aba do scanner rapido:
   - Banner explicando que tipo de teste e
   - Botoes **Iniciar scan** (verde) e **Parar** (vermelho)
   - Pede senha admin ao iniciar
   - Log streaming: vai aparecendo o que ele esta checando em
     tempo real
   - **Amarelo** = warning (possivel falso positivo)
   - **Vermelho** = INFECTED (alerta serio)
   - No fim, summary: testes rodados, warnings, infectados

2. **Rootkit Hunter** — Mesma coisa mas mais demorado e mais
   completo (200+ verificacoes).

3. **Historico** — Lista todos os scans que voce ja fez. Pode
   abrir um antigo pra revisar.

4. **Sobre** — Manual interno.

## O que cada parte faz

- **Banner colorido** no topo — avisa se o scanner nao esta instalado.
- **Iniciar scan** — comeca o trabalho. Vai pedir sua senha (pkexec).
- **Parar** — interrompe se demorar demais.
- **Log streaming** — vai mostrando o que esta checando agora mesmo.
- **Findings** (avisos coloridos) — qualquer coisa suspeita destacada.
- **Summary** no fim — resumo do scan.
- **Historico** — todos os scans ficam salvos em JSON na sua pasta
  pessoal (`~/.local/share/vigia-rootkit/scans/`), com permissao
  **so voce le**.

## Posso quebrar alguma coisa?

**Nao.** Estes scanners sao **somente leitura** — eles soh **olham**
o sistema procurando padroes suspeitos. Nao apagam nada, nao mexem
em arquivo.

Voce pode rodar os scans a vontade, quantas vezes quiser. O risco
maximo e perder uns minutos de espera.

## Como interpretar o resultado

**Limpo** (tudo verde) — nenhum sinal de rootkit. Sistema OK.

**Warning** (amarelo) — **possivel** falso positivo. Causas comuns:
- Voce fez `rpm-ostree upgrade` recente e alguns arquivos mudaram
- Voce tem drivers proprietarios (NVIDIA, VirtualBox) instalados
- Sua configuracao SSH e diferente do padrao (pode estar OK)

**Infected** (vermelho) — **alta probabilidade** de comprometimento.
Se aparecer:

1. **Desconecte o computador da rede** (cabo ou WiFi).
2. **Salve o report** — esta em `~/.local/share/vigia-rootkit/scans/`.
3. **Rode o outro scanner** (se rodou chkrootkit, rode rkhunter
   tambem) pra cross-check.
4. **Compare com o File Integrity** (AIDE) — outra tool do Vigia que
   ve mudancas em arquivos importantes.
5. **Considere reinstalar o sistema** se realmente foi comprometido.
   Em sistemas atomicos (Silverblue), isso pode ser facilitado pelo
   **Deployments Manager** (voltar pra deployment anterior).

**Importante**: warnings sao comuns e muitas vezes inofensivos. Nao
entre em panico. Confirme com o outro scanner e com o File Integrity
antes de tomar acao drastica.

## Dica do dia

**Rode os dois scanners juntos: chkrootkit primeiro, depois Rootkit
Hunter.**

- chkrootkit (~30s) e seu primeiro pente-fino.
- Rootkit Hunter (2-5min) e o exame completo.

Se os **dois** acusarem algo serio (INFECTED), tome a coisa muito a
serio.

Se **soh um** acusa, e provavelmente **falso positivo** — confirma
checando o nome do teste no Google. Muitos warnings no rkhunter
sao "esperados" em sistemas modernos (Silverblue, Bluefin, etc).

E **mantenha a base do rkhunter atualizada** rodando periodicamente
no terminal:
```
sudo rkhunter --update
```
(Voce pode pedir pra alguem que entenda ajudar com isso. Ou esperar
a v0.3 do Vigia que vai automatizar.)
