# Vigia Intel — lista de "procurados" digitais (para leigos)

## O que é

O **Vigia Intel** é como uma **lista de procurados** do mundo digital. Você guarda
nela os **indicadores de coisas ruins** já conhecidas — endereços de internet (IPs),
sites (domínios), links (URLs), "impressões digitais" de arquivos (hashes) e
e-mails usados em golpes. Depois, quando você tem um suspeito, pergunta ao Vigia
Intel: *"esse aqui já é conhecido como malicioso?"*.

Esses indicadores têm um nome técnico: **IOC** (*Indicator of Compromise*).

## Para que serve

- Pegar os **IPs que o Vigia SIEM** mostrou (força-bruta, bloqueios do fail2ban) e
  checar se já são **conhecidos como atacantes**.
- Conferir se o **hash de um arquivo** suspeito bate com algum malware conhecido.
- Ver se um **site/link** recebido por e-mail está na sua lista de perigosos.

## Como usar

### Verificar
1. Vá na aba **Verificar**.
2. **Cole os indicadores** (um por linha) — IPs, domínios, hashes, etc.
3. Clique em **Verificar**.
4. O Vigia Intel mostra **quais casaram** com a sua base. Cada resultado é um
   botão: clique para ver o **tipo**, a **fonte** e a **nota** daquele indicador.

### Montar e alimentar a base (aba IOCs)
- **Adicionar** um indicador de cada vez (o tipo é detectado sozinho).
- **Importar de arquivo**: uma lista em texto, ou um **export do OTX**
  (AlienVault) ou do **MISP** (`.json`) que você baixou. Não precisa de internet
  nem de senha de API na hora de checar.
- **Remover** indicadores que não quer mais (lixeirinha ao lado).

## Importante

- A base é **sua** — começa vazia. Quanto mais boa informação você colocar (de
  fontes confiáveis), melhor o Vigia Intel responde.
- Um indicador **não estar na base** não garante que é seguro — só significa que
  você ainda não o conhece. E estar na base é um **forte sinal de perigo**.

## Privacidade

Funciona **offline**: a base fica só na sua máquina, protegida (permissão 0600).
A checagem não envia nada para lugar nenhum.
