# Monitor do Sistema

## Pra que serve

O **Monitor do Sistema** é o **painel do carro** do seu computador. Em vez de velocímetro e tacômetro, ele te mostra **quanto** o computador está sendo usado em **tempo real**: CPU (cérebro), memória (RAM), disco (HD/SSD), rede (internet) e quais programas estão rodando.

Se você já usou Gerenciador de Tarefas no Windows ou Monitor de Atividade no Mac, é a **mesma ideia** — só que com gráficos mais bonitos e numa interface que combina com o resto do GNOME.

## Quando você usa isso

- O computador está **lento** e você quer saber **quem está puxando recursos**
- Você quer **matar** um programa que travou (tipo um Chrome que comeu 8GB de RAM)
- Quer ver se o **disco está saturado** quando você copia arquivos grandes
- Quer **configurar alarme** pra ser avisado quando algo passar dos limites (RAM em 90%, CPU em 95%, temperatura em 85°C)
- Só curiosidade — saber o que está acontecendo no fundo

## O que você vai ver

Seis abas no topo. Cada uma com sua especialidade. Os gráficos são **coloridos com propósito**:

- **Verde** (esmeralda) é CPU
- **Amarelo** (âmbar) é Memória/RAM
- **Azul** (ciano) é Disco
- **Roxo** (violeta) é Rede

Quando você vê picos de uma cor específica, você sabe **na hora** qual área do PC está sob pressão.

## O que cada parte faz

### Aba 1 — Visão Geral

A "página inicial". Mostra **nome do PC** e, logo abaixo, um **selo colorido com o seu sistema** (ex.: *Fedora Workstation*). Assim você sabe na hora qual versão do Fedora está rodando. Mostra também a distribuição Linux, há quanto tempo está ligado, e **3 cartões de Load Average** (uma métrica que mostra se o sistema está sobrecarregado). Tem **gráficos mini** (sparklines) de CPU, RAM e Internet (download/upload). E uma lista de discos com **barras de uso** e os top 3 programas comendo mais CPU e RAM.

É o resumo de tudo numa tela só.

### Aba 2 — Recursos

Os gráficos **detalhados**, um pra cada componente:

- **CPU** — uso de cada núcleo separado, frequência atual e **temperatura**
- **Memória** — quanto está usada, quanto é cache, quanto está livre (e swap, se você usa)
- **Disco** — quanto está usado em cada partição e velocidade de leitura/escrita
- **Rede** — velocidade de download/upload em cada interface (Wi-Fi, cabo, etc)

### Aba 3 — Processos

A **lista de programas rodando**. Top 30 por padrão. Você pode:

- **Buscar** por nome ("chrome", "firefox")
- **Ordenar** por CPU, memória, disco, conexões, PID ou nome
- **Filtrar só os seus** processos (esconde os do sistema)
- **Matar** um processo com o botão Kill (pede confirmação)

Se você tenta matar um processo que **não é seu** (do sistema), ele pede senha de admin automaticamente.

### Aba 4 — Rede

Mostra **quanto de internet cada programa está usando agora** — quem está baixando ou enviando dados. Você clica em **"Medir banda"**, digita a senha de administrador, e em ~4 segundos ele lista os programas por tráfego (↑ enviado · ↓ recebido).

Pra que serve de verdade: descobrir **quem está comendo sua banda**, ou **flagrar um programa suspeito mandando dados pra fora** (exfiltração). O tráfego que o sistema não consegue ligar a um programa aparece pelo **endereço de destino** — ainda útil pra ver *pra onde* os dados estão indo.

> Precisa do **nethogs** instalado (Instalador → Monitoramento → nethogs) — sem ele, a aba avisa. E precisa de **rede ativa** durante a medição: pra ver dados, deixe um download rolando e clique em Medir.

### Aba 5 — Alertas

Você **configura limites**. Por exemplo: "me avisa quando CPU passar de 95% por mais de 30 segundos". O Monitor do Sistema fica monitorando em background, **mesmo quando você está em outra aba**, e te notifica quando o limite for batido.

Métricas disponíveis:

- Uso de CPU (%)
- Uso de RAM (%)
- Uso de Swap (%)
- Load average de 1 minuto
- **Temperatura da CPU** (°C)
- Uso de disco em `/` e em `/home`

Para cada regra você define **quanto tempo** o problema precisa persistir pra disparar (evita falso-positivo de pico instantâneo) e **quanto esperar** entre dois alertas iguais (cooldown).

### Aba 6 — Sobre

Informações do programa.

## Termos que você vai ver

- **CPU** — o "cérebro" do computador. Quanto maior o uso, mais lento sente.
- **RAM / Memória** — a "mesa de trabalho". Quando enche, o computador começa a usar disco como memória (swap) e fica MUITO lento.
- **Swap** — espaço no disco usado como memória extra quando a RAM enche. Usar swap = sinal de pressão de memória.
- **Load average** — quantos processos estão "esperando vez" no CPU. Se for maior que o número de núcleos, o sistema está sobrecarregado.
- **PID** — número de identificação único de cada programa rodando. Aparece na aba Processos.

## Posso quebrar alguma coisa?

Quase não. As **únicas ações destrutivas** são:

- **Matar processo** (aba Processos) — pode fechar um programa que você tinha trabalho aberto. Sempre pede confirmação. Para processo de outro usuário, pede senha.

Tudo mais é **somente leitura**: o Monitor do Sistema apenas **olha** o que o kernel já sabe e te mostra. Não modifica nada do sistema, não acessa internet, não salva nada em disco (exceto suas regras de alarme).

## Dica do dia

> Deixe o Monitor do Sistema na aba **Visão Geral** com o Hub minimizado na bandeja. Quando perceber **lentidão**, expanda o Hub e olha pros sparklines: a cor do pico já te diz onde investigar (verde = CPU, amarelo = RAM, ciano = disco, roxo = rede). Em 5 segundos você sabe pra onde ir.

## Onde encontrar mais

Esse Monitor do Sistema substitui as ferramentas clássicas de terminal: **htop**, **btop**, **glances**, **iotop** e **iftop**. Se você já conhece elas, sabe o que esperar — mas aqui está tudo numa interface visual moderna sem precisar abrir terminal.
