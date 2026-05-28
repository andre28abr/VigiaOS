# Gerenciador de DNS

## Pra que serve

Esconde dos provedores de internet **quais sites voce visita**.

Pra entender o problema: toda vez que voce digita `google.com`, seu
computador pergunta pra um servidor de DNS qual e' o IP do Google. Essa
pergunta vai em **texto puro** pela rede. Quem ve essas perguntas?
- Seu provedor de internet (Vivo, Claro, Oi)
- O dono do Wi-Fi do cafe / aeroporto / hotel
- Qualquer um na mesma rede
- E, em alguns casos, o governo

O Gerenciador de DNS faz suas perguntas viajarem **criptografadas**,
usando uma tecnologia chamada DNS over HTTPS (DoH).

Quem ve a pergunta agora? **Ninguem**. Nem seu provedor. Nem o cafe.

## Quando voce usa isso

- **Toda vez que voce conecta numa rede que nao confia** (cafe, hotel,
  aeroporto).
- **Pra cumprir LGPD**: privacidade dos dados de navegacao dos clientes
  no escritorio.
- **Pra bloquear sites de propaganda no nivel de rede**: AdGuard e
  Mullvad AdBlock filtram anuncios antes mesmo de chegar no navegador
  — funciona pra todos os apps, nao so o Firefox.
- **Pra impedir DNS poisoning**: garantir que voce esta chegando no
  banco verdadeiro e nao numa copia falsa.

## O que voce vai ver

A janela tem **3 abas**:

**Status**: o "painel de controle". Mostra um cabecalho gigante:
- "Ativo e seguro" (verde): tudo certo, sua privacidade DNS esta ligada
- "dnscrypt-proxy parado" (amarelo): instalado mas nao rodando
- "Quase la" (amarelo): rodando, mas sistema ainda nao usa
- "nao instalado" (vermelho): precisa instalar antes

Tem 2 botoes principais: **Ativar dnscrypt-proxy** (liga tudo de uma
vez) e **Restaurar systemd-resolved** (volta ao padrao do sistema, se
quiser parar de usar).

**Provedores**: lista de **11 provedores curados** pra escolher. Eles
sao:
- **Cloudflare** (rapido, sem logs, sem filtro) — recomendado
- **Cloudflare Security** (bloqueia malware)
- **Cloudflare Family** (bloqueia malware + conteudo adulto)
- **Quad9** (suico, filtra dominios maliciosos)
- **AdGuard** (bloqueia anuncios)
- **AdGuard Family** (anuncios + adulto)
- **Mullvad** (sueco, sem logs)
- **Mullvad AdBlock** (sueco + anuncios)
- **Quad9 DNSCrypt** (alternativa quando bloqueiam HTTPS)
- **Anonymized Relay** (esconde seu IP do servidor final)

Cada um tem etiquetas mostrando: protocolo, se guarda logs, se filtra,
se valida DNSSEC, e em que pais fica.

Voce escolhe, clica em **Aplicar**, digita a senha, e pronto.

**Sobre**: explicacao detalhada.

## O que cada parte faz

- **dnscrypt-proxy**: o programa que faz a magica. E' um servico que
  roda no seu computador (em `127.0.0.1`) e funciona como
  "intermediario" entre seus apps e os servidores DNS criptografados.
- **DoH** (DNS over HTTPS): suas perguntas viajam dentro de trafego
  HTTPS — igualzinho a um site bancario, indistinguivel pra quem esta
  espionando.
- **DNSSEC**: garantia matematica de que a resposta nao foi adulterada
  no caminho.
- **No-logs**: o provedor promete nao guardar registro das suas
  consultas.
- **Anonymized DNS**: usa um intermediario que esconde seu IP do
  servidor final (similar ao Tor, mas so pra DNS).

### Combinacao recomendada

Pra **uso geral**: Cloudflare (rapido).
Pra **escritorio LGPD**: Mullvad AdBlock (bloqueia tracking corporativo
+ sueco, jurisdicao boa).
Pra **familia**: Cloudflare Family ou AdGuard Family.

## Posso quebrar alguma coisa?

**Sim, com cuidado.** Essa ferramenta muda o DNS do **sistema inteiro**
— se algo der errado, sua internet pode parar de funcionar
temporariamente.

Mas a ferramenta tem **backup automatico** de tudo. Se quiser voltar
atras, basta clicar em "Restaurar systemd-resolved" na aba Status. Em
3 segundos voce volta ao normal.

**Cuidado especial**: voce precisa ter o programa `dnscrypt-proxy`
instalado antes. Se nao tiver, o Status vai mostrar "nao instalado" e
voce vai precisar passar pelo **Instalador de Ferramentas** primeiro.

## Dica do dia

Pra um escritorio de advocacia que precisa cumprir LGPD:

1. **Instalador de Ferramentas** -> instale `dnscrypt-proxy`
2. Reinicie.
3. **DNS Manager** -> Status -> "Ativar dnscrypt-proxy".
4. **DNS Manager** -> Provedores -> "Mullvad AdBlock". Aplicar.
5. Pronto. Tracking corporate bloqueado, queries DNS criptografadas e
   anonimas, sem precisar instalar Pi-hole em hardware separado.

Pra testar se esta funcionando: visite **https://dnsleaktest.com**.
Voce deveria ver o servidor da Mullvad/Cloudflare, **nao o do seu
provedor**. Se aparecer "Vivo" ou "Claro", algo nao esta certo.
