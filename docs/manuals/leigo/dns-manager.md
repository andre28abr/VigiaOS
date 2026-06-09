# Gerenciador de DNS

## Pra que serve

Esconde dos provedores de internet **quais sites você visita**.

Pra entender o problema: toda vez que você digita `google.com`, seu
computador pergunta pra um servidor de DNS qual é o IP do Google. Essa
pergunta vai em **texto puro** pela rede. Quem vê essas perguntas?
- Seu provedor de internet (Vivo, Claro, Oi)
- O dono do Wi-Fi do café / aeroporto / hotel
- Qualquer um na mesma rede
- E, em alguns casos, o governo

O Gerenciador de DNS faz suas perguntas viajarem **criptografadas**,
usando uma tecnologia chamada DNS over HTTPS (DoH).

Quem vê a pergunta agora? **Ninguém**. Nem seu provedor. Nem o café.

## Quando você usa isso

- **Toda vez que você conecta numa rede que não confia** (café, hotel,
  aeroporto).
- **Pra cumprir LGPD**: privacidade dos dados de navegação dos clientes
  no escritório.
- **Pra bloquear sites de propaganda no nível de rede**: AdGuard e
  Mullvad AdBlock filtram anúncios antes mesmo de chegar no navegador
  — funciona pra todos os apps, não só o Firefox.
- **Pra impedir DNS poisoning**: garantir que você está chegando no
  banco verdadeiro e não numa cópia falsa.

## O que você vai ver

A janela tem **3 abas**:

**Status**: o "painel de controle". Mostra um cabeçalho gigante:
- "Ativo e seguro" (verde): tudo certo, sua privacidade DNS está ligada
- "dnscrypt-proxy parado" (amarelo): instalado mas não rodando
- "Quase lá" (amarelo): rodando, mas sistema ainda não usa
- "não instalado" (vermelho): precisa instalar antes

Tem 2 botões principais: **Ativar dnscrypt-proxy** (liga tudo de uma
vez) e **Restaurar systemd-resolved** (volta ao padrão do sistema, se
quiser parar de usar).

**Provedores**: lista de **11 provedores curados** pra escolher. Eles
são:
- **Cloudflare** (rápido, sem logs, sem filtro) — recomendado
- **Cloudflare Security** (bloqueia malware)
- **Cloudflare Family** (bloqueia malware + conteúdo adulto)
- **Quad9** (suíço, filtra domínios maliciosos)
- **AdGuard** (bloqueia anúncios)
- **AdGuard Family** (anúncios + adulto)
- **Mullvad** (sueco, sem logs)
- **Mullvad AdBlock** (sueco + anúncios)
- **Quad9 DNSCrypt** (alternativa quando bloqueiam HTTPS)
- **Anonymized Relay** (esconde seu IP do servidor final)

Cada um tem etiquetas mostrando: protocolo, se guarda logs, se filtra,
se valida DNSSEC, e em que país fica.

Você escolhe, clica em **Aplicar**, digita a senha, e pronto.

**Sobre**: explicação detalhada.

## O que cada parte faz

- **dnscrypt-proxy**: o programa que faz a mágica. É um serviço que
  roda no seu computador (em `127.0.0.1`) e funciona como
  "intermediário" entre seus apps e os servidores DNS criptografados.
- **DoH** (DNS over HTTPS): suas perguntas viajam dentro de tráfego
  HTTPS — igualzinho a um site bancário, indistinguível pra quem está
  espionando.
- **DNSSEC**: garantia matemática de que a resposta não foi adulterada
  no caminho.
- **No-logs**: o provedor promete não guardar registro das suas
  consultas.
- **Anonymized DNS**: usa um intermediário que esconde seu IP do
  servidor final (similar ao Tor, mas só pra DNS).

### Combinação recomendada

Pra **uso geral**: Cloudflare (rápido).
Pra **escritório LGPD**: Mullvad AdBlock (bloqueia tracking corporativo
+ sueco, jurisdição boa).
Pra **família**: Cloudflare Family ou AdGuard Family.

## Posso quebrar alguma coisa?

**Sim, com cuidado.** Essa ferramenta muda o DNS do **sistema inteiro**
— se algo der errado, sua internet pode parar de funcionar
temporariamente.

Mas a ferramenta tem **backup automático** de tudo. Se quiser voltar
atrás, basta clicar em "Restaurar systemd-resolved" na aba Status. Em
3 segundos você volta ao normal.

**Cuidado especial**: você precisa ter o programa `dnscrypt-proxy`
instalado antes. Se não tiver, o Status vai mostrar "não instalado". Pra
instalar, abra o terminal e rode `sudo dnf install dnscrypt-proxy` (ou
mantenha o sistema em dia pela aba **Configurações → Atualizações**).

## Dica do dia

Pra um escritório de advocacia que precisa cumprir LGPD:

1. **Terminal** -> `sudo dnf install dnscrypt-proxy`
2. **DNS Manager** -> Status -> "Ativar dnscrypt-proxy".
3. **DNS Manager** -> Provedores -> "Mullvad AdBlock". Aplicar.
4. Pronto. Tracking corporate bloqueado, queries DNS criptografadas e
   anônimas, sem precisar instalar Pi-hole em hardware separado.

Pra testar se está funcionando: visite **https://dnsleaktest.com**.
Você deveria ver o servidor da Mullvad/Cloudflare, **não o do seu
provedor**. Se aparecer "Vivo" ou "Claro", algo não está certo.
