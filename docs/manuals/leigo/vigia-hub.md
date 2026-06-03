# Vigia Hub

## Pra que serve

O **Vigia Hub** é o aplicativo que junta todas as ferramentas do VigiaOS numa **janela só**. Sem ele, você teria que abrir um app diferente toda vez que quisesse ver os logs, mexer no firewall ou checar se o sistema está seguro. Pense nele como o **painel de controle** do seu computador — uma porta única de entrada pra tudo.

Você abre o Hub, e ele te mostra na lateral as ferramentas disponíveis (Dashboard, Activity Log, Privacy Controls e mais). Clica em uma, e ela aparece **dentro da mesma janela**. Sem cinco janelas abertas no Alt+Tab.

## Quando você usa isso

- Você vai usar o Vigia Hub mais de uma vez por mês — então quer ter ele **a um clique** na bandeja do sistema
- Quer **proteger o acesso** ao painel com senha (caso outra pessoa pegue seu PC)
- Quer que o Hub abra junto com o computador, já minimizado, esperando você
- Quer **ler os manuais** das ferramentas sem precisar abrir o navegador
- Vai usar a maquina em ambiente compartilhado (escritório, sala de reunião) e precisa de uma camada extra de proteção

## O que você vai ver

Quando você abre o Hub, a janela tem **três partes**:

1. **Uma barra fininha na esquerda** com 5 botões-ícone: Módulos (as ferramentas), Instalador, Config., Ajuda e Sobre.
2. **Uma lista no meio** com todas as ferramentas, agrupadas por tipo: Monitoramento, Privacidade, Defesa & Hardening, Sistema, Relatórios.
3. **A área grande da direita** que mostra a ferramenta escolhida em tela cheia.

Cada ferramenta na lista tem um **ícone**, um **nome**, uma **descrição curta** e um **pontinho verde** (instalada) ou **vermelho** (não instalada).

Em cima de cada ferramenta abrindo no painel, você vê uma faixa com pequenos **badges cinza** dizendo "Wrapper de: lynis", "Wrapper de: dconf systemctl" — isso é só pra você saber **qual programa do Linux** aquela ferramenta está usando por baixo dos panos.

## O que cada parte faz

### Tools (a parte principal)

A lista das ferramentas. Clica e ela abre. Pronto. As principais são **Dashboard** (monitor de sistema), **Activity Log** (logs traduzidos), **Privacy Controls** (toggles de privacidade), **Firewall**, **Antivirus**, **Reports** e algumas outras.

### Instalador

Tela cheia que abre o **Tool Installer** — ele instala pacotes do Fedora que algumas ferramentas precisam (Lynis, ClamAV, AIDE, etc) e tem a aba **Atualizações** pra manter tudo em dia.

Quando o Hub abre, ele dá uma olhada (sozinho, sem senha) se há atualizações — do sistema ou dos seus programas de segurança. Se houver, o **sininho de notificações** lá no rodapé da barra da esquerda ganha uma **bolinha vermelha**; clica nele e abre um menuzinho mostrando o que há. É só um aviso: não instala nada sozinho. Dá pra ligar/desligar em Configurações → Aplicação.

### Configurações

Duas abas (o **Sobre** agora é um ícone próprio na barra da esquerda):

- **Aplicação** — Liga o Hub junto com o sistema, mostra ícone na bandeja, inicia minimizado e **verifica atualizações ao iniciar** (alimenta o sininho de notificações).
- **Segurança** — Pede senha de admin pra abrir o Hub e auto-bloqueia se você ficar X minutos sem mexer (5, 10, 15, 30 ou 60 minutos).

### Ajuda

Manuais de todas as ferramentas, divididos em "Visão geral", "Manual técnico" e "Manual simples" (esse aqui que você está lendo).

## Termos que você vai ver

- **Bandeja do sistema (tray)** — o cantinho perto do relógio do GNOME, onde aparecem ícones de apps minimizados. No GNOME vanilla do Fedora Workstation precisa instalar uma extensão pra essa área existir.
- **Autostart** — opção que faz o Hub abrir sozinho toda vez que você liga o computador.
- **pkexec / Polkit** — o sistema do Linux que pede sua senha de admin com aquele diálogo cinza padrão do GNOME. O Hub nunca guarda sua senha; ele só pede pro Polkit perguntar.
- **Lock** — quando o Hub está "bloqueado", ele esconde a janela e pede sua senha de admin pra reabrir.

## Posso quebrar alguma coisa?

**Não.** O Hub é um **launcher** — ele só abre outras ferramentas. Quem mexe no sistema são as ferramentas em si. O Hub apenas:

- Salva suas preferências em `~/.config/vigia-hub/settings.json` (só você lê)
- Pode criar um arquivo de autostart em `~/.config/autostart/` se você ligar essa opção
- Pede senha de admin **apenas** se você explicitamente ligar o "Exigir senha para abrir o Hub"

Nenhuma dessas coisas afeta outros programas ou outros usuários da máquina.

## Dica do dia

> Liga o **autostart** + **iniciar minimizado na bandeja** + **tray icon** juntos. Resultado: você liga o computador, o Hub fica esperando perto do relógio, e você abre com um clique. Sem ocupar tela enquanto você trabalha em outras coisas.

Bônus: se também ligar o **password lock**, o Hub só pede senha quando você realmente clicar pra abrir — não pede no boot, pra não atrapalhar a inicialização do sistema.

## Onde encontrar mais

Cada ferramenta tem **seu próprio manual** dentro da aba **Ajuda** do Hub. Você não precisa sair pra navegador nem ler README no GitHub. Se quiser detalhes técnicos profundos, troca a sub-aba pra **"Manual técnico"** ali mesmo.
