# Vigia SIEM — detector de eventos suspeitos (para leigos)

## O que é

O **Vigia SIEM** é o "vigia de plantão" do seu computador. Ele lê os **registros
do sistema** (os "diários de bordo" que o Linux mantém o tempo todo) e procura
**padrões suspeitos** — sinais de que alguém pode estar tentando invadir, ganhar
poder de administrador ou esconder rastros.

Em vez de você ter que ler milhares de linhas técnicas, o Vigia SIEM faz isso por
você e te entrega só o que importa: **alertas**, em português, com a explicação do
que é e o que fazer.

> **SIEM** é como o mercado de segurança chama esse tipo de ferramenta
> (*Security Information and Event Management*). Aqui ela é simples e local.

## Para que serve

- Saber se houve **tentativas de invasão** (ex.: alguém tentando adivinhar sua
  senha por SSH).
- Perceber se alguém tentou **virar administrador** (sudo/su) sem permissão.
- Descobrir se foi **criado um usuário novo** que você não reconhece.
- Ver **bloqueios do SELinux**, **falhas de serviço** e **software instalado**.
- Confirmar que sua defesa (**fail2ban**) está funcionando e bloqueando IPs.

## Qual a diferença para o Activity Log?

O **Activity Log** (no VigiaHub) é como **assistir à gravação inteira** da câmera:
mostra *tudo* o que aconteceu, em ordem. O **Vigia SIEM** é como ter um **segurança
que assiste por você e só te chama quando vê algo estranho**. Mesma câmera, trabalhos
diferentes — um é para navegar, o outro é para **detectar**.

## Como usar

1. Abra a aba **Alertas**.
2. (Opcional) Ligue **"Incluir o log de auditoria (audit)"** para uma análise mais
   completa — isso pede sua **senha de administrador** (uma janelinha do sistema).
   Sem ligar, ele já analisa o que dá sem senha.
3. Clique em **Analisar agora**.
4. Veja os **alertas**:
   - **Nenhum alerta** → nada suspeito nos registros recentes. 👍
   - **Um ou mais alertas** → cada alerta é um **botão**. Aparece um **título** e a
     **severidade** (Info / Baixo / Suspeito / Alto / Crítico). **Clique** para abrir:
     - **O que é** — explicação em português;
     - **O que fazer** — a recomendação prática;
     - **Quando** — o período em que aconteceu;
     - **Ocorrências** — quantas vezes;
     - **Evidência (técnico)** — as linhas reais do log, para quem quer o detalhe.

> Um alerta **não é prova** de ataque — é um aviso de que algo merece um olhar.
> A parte "O que é" e "O que fazer" te ajudam a decidir se é grave.

## As regras (o que ele procura)

A aba **Regras** lista tudo o que o Vigia SIEM sabe detectar. Hoje são **7**:

- **Força-bruta de login (SSH)** — muitas tentativas de senha erradas da mesma
  origem. *Alto.*
- **Falha de elevação (sudo/su)** — alguém tentou virar administrador e não
  conseguiu. *Suspeito.*
- **Conta de usuário criada/alterada** — usuário ou grupo novo/mudado. *Suspeito.*
- **Falha de serviço do sistema** — um serviço caiu ou deu erro. *Baixo.*
- **Bloqueio do SELinux** — a proteção do sistema barrou uma ação. *Suspeito.*
- **Software instalado ou removido** — mudança nos programas. *Info.*
- **IP bloqueado pelo fail2ban** — sua defesa bloqueou um atacante. *Suspeito.*

A severidade vai de **Info** (só informativo) até **Crítico** (urgente). Os alertas
aparecem **ordenados** — os mais graves primeiro.

## Histórico

Toda análise fica salva (só na sua máquina, protegida) e aparece na aba
**Histórico**, para você comparar com o tempo.

## Privacidade

O Vigia SIEM roda **100% local**: nada sai da sua máquina. Os relatórios são salvos
com permissão restrita (só você lê). Ele **lê** os registros do sistema, não muda nada.
