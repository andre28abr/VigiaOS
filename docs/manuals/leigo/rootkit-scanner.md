# Verificador de Rootkit

## Pra que serve

Pra **descobrir se tem alguém espionando seu computador escondido**.

Um **rootkit** é um tipo de malware muito perigoso porque ele se
**esconde** do sistema. Você não vê o processo dele, não vê os
arquivos dele. Ele pode estar lá há meses, lendo seus emails,
capturando senhas, mandando seus dados pra fora — e você não percebe.

Este Verificador roda **dois programas clássicos** que sabem procurar
sinais de rootkit:

- **chkrootkit** — rápido (~30 segundos)
- **Rootkit Hunter** (rkhunter) — completo (2 a 5 minutos, 200+ checagens)

São complementares: rode os dois pra ter cobertura cruzada.

## Quando você usa isso

- **Quando o computador está agindo estranho** sem motivo aparente:
  lento, fan trabalhando, conexões de rede inexplicáveis.
- **Periodicamente** (1x/mês) como audit baseline.
- **Depois de uma atualização grande** do sistema.
- **Após compartilhar o computador** com alguém desconhecido.
- **Em servidor** que ficou exposto à internet, mesmo brevemente.
- **Audit LGPD** — comprovar que você verifica integridade
  periodicamente.

## O que você vai ver

São **4 abas**:

1. **chkrootkit** — Aba do scanner rápido:
   - Banner explicando que tipo de teste é
   - Botões **Iniciar scan** (verde) e **Parar** (vermelho)
   - Pede senha admin ao iniciar
   - Log streaming: vai aparecendo o que ele está checando em
     tempo real
   - **Amarelo** = warning (possível falso positivo)
   - **Vermelho** = INFECTED (alerta sério)
   - No fim, summary: testes rodados, warnings, infectados

2. **Rootkit Hunter** — Mesma coisa mas mais demorado e mais
   completo (200+ verificações).

3. **Histórico** — Lista todos os scans que você já fez. Pode
   abrir um antigo pra revisar.

4. **Sobre** — Manual interno.

## O que cada parte faz

- **Banner colorido** no topo — avisa se o scanner não está instalado.
- **Iniciar scan** — começa o trabalho. Vai pedir sua senha (pkexec).
- **Parar** — interrompe se demorar demais.
- **Log streaming** — vai mostrando o que está checando agora mesmo.
- **Findings** (avisos coloridos) — qualquer coisa suspeita destacada.
- **Summary** no fim — resumo do scan.
- **Histórico** — todos os scans ficam salvos em JSON na sua pasta
  pessoal (`~/.local/share/vigia-rootkit/scans/`), com permissão
  **só você lê**.

## Posso quebrar alguma coisa?

**Não.** Estes scanners são **somente leitura** — eles só **olham**
o sistema procurando padrões suspeitos. Não apagam nada, não mexem
em arquivo.

Você pode rodar os scans à vontade, quantas vezes quiser. O risco
máximo é perder uns minutos de espera.

## Como interpretar o resultado

**Limpo** (tudo verde) — nenhum sinal de rootkit. Sistema OK.

**Warning** (amarelo) — **possível** falso positivo. Causas comuns:
- Você fez `sudo dnf upgrade` recente e alguns arquivos mudaram
- Você tem drivers proprietários (NVIDIA, VirtualBox) instalados
- Sua configuração SSH é diferente do padrão (pode estar OK)

**Infected** (vermelho) — **alta probabilidade** de comprometimento.
Se aparecer:

1. **Desconecte o computador da rede** (cabo ou WiFi).
2. **Salve o report** — está em `~/.local/share/vigia-rootkit/scans/`.
3. **Rode o outro scanner** (se rodou chkrootkit, rode rkhunter
   também) pra cross-check.
4. **Compare com o File Integrity** (AIDE) — outra tool do Vigia que
   vê mudanças em arquivos importantes.
5. **Considere reinstalar o sistema** se realmente foi comprometido.

**Importante**: warnings são comuns e muitas vezes inofensivos. Não
entre em pânico. Confirme com o outro scanner e com o File Integrity
antes de tomar ação drástica.

## Dica do dia

**Rode os dois scanners juntos: chkrootkit primeiro, depois Rootkit
Hunter.**

- chkrootkit (~30s) é seu primeiro pente-fino.
- Rootkit Hunter (2-5min) é o exame completo.

Se os **dois** acusarem algo sério (INFECTED), tome a coisa muito a
sério.

Se **só um** acusa, é provavelmente **falso positivo** — confirma
checando o nome do teste no Google. Muitos warnings no rkhunter
são "esperados" em sistemas Linux modernos.

E **mantenha a base do rkhunter atualizada** rodando periodicamente
no terminal:
```
sudo rkhunter --update
```
(Você pode pedir pra alguém que entenda ajudar com isso. Ou esperar
a v0.3 do Vigia que vai automatizar.)
