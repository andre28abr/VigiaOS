# Vigia IDS — alarme de intrusão na rede (para leigos)

## O que é

O **Vigia IDS** é como o **alarme de uma casa, mas para a sua rede**. Um IDS
(*Intrusion Detection System*, ou "sistema de detecção de intrusão") fica de olho
no tráfego de rede e dispara um aviso quando vê algo típico de ataque — uma
varredura de portas, uma tentativa de exploração, um acesso a um site malicioso.

O Vigia IDS usa o **Suricata**, um dos IDS de rede mais usados do mundo, e mostra
os alertas dele de forma **organizada e em português**, por gravidade.

## Para que serve

- Ver, de forma simples, **o que o Suricata detectou** na sua rede.
- Investigar uma captura de rede (`.pcap`) procurando sinais de ataque.
- Entender **quem** (origem), **para onde** (destino) e **o quê** de cada alerta.

## Como usar

Há dois jeitos de dar uma fonte de alertas ao Vigia IDS:

### 1) Ler o eve.json de um Suricata que já roda
Se você (ou a TI) já tem o Suricata monitorando a rede, ele grava tudo num arquivo
chamado **`eve.json`** (normalmente em `/var/log/suricata/eve.json`).
1. Na aba **Alertas**, o Vigia IDS tenta achar esse arquivo sozinho. Se não achar,
   clique em **Selecionar** e aponte para ele.
2. Clique em **Analisar eve.json**.

### 2) Analisar um arquivo de captura (.pcap)
Se você tem uma **captura de rede** (um arquivo `.pcap`, feito por exemplo com o
Wireshark) e o **Suricata está instalado** nesta máquina:
1. Clique em **Selecionar .pcap** e escolha a captura.
2. O Vigia IDS roda o Suricata sobre ela e mostra os alertas.

### Lendo os resultados
Cada alerta é um **botão**: aparece o nome do ataque detectado e a **gravidade**
(Info / Baixo / Suspeito / Alto). **Clique** para ver:
- **Origem** e **Destino** (quem falou com quem, IP e porta);
- **Protocolo**;
- **Quando** aconteceu;
- a **assinatura (SID)** — o número da regra do Suricata, para o detalhe técnico.

Os alertas vêm **ordenados** — os mais graves primeiro.

## Histórico

Cada análise fica salva (só na sua máquina, protegida) e aparece na aba
**Histórico**.

## Privacidade

Roda **local**. Só **lê** os alertas — não muda nada na rede. Os relatórios ficam
na sua máquina com permissão restrita (0600).
