# Configurando o Traefik   

Nesse apêndice vou colocar as configurações realizadas no container do `Traefik`, que será o nosso Reverse Proxy tanto para o Back quanto para o Front. Optei por usar o Traefik porque acho mais simples de configurar do que o Nginx. 

!!! tip

    Se você não conhece o Traefik, sugiro assistir a esse vídeo:
    
    [Simple HTTPs for Docker! // Traefik Tutorial](https://www.youtube.com/watch?v=-hfejNXqOzA)

## Criando uma Network no Docker

Todos os containers que usam o Traefik como Proxy Reverso precisarão estar em uma mesma network, então vou criá-la manualmente e dar o nome de `my-network`. Acessando o servidor de produção (minha VPS da Hostinger), vou dar o comando:

```bash
docker network create my-network
```

## Criando a estrutura de pastas

Criarei uma pasta chamada `traefik`, onde armazenaremos o nosso arquivo de compose, e nessa pasta vou criar mais dois diretórios, um chamado `config` (onde teremos os arquivos de configuração), e outro chamado `certs`, onde armazenaremos os certificados assinados. A estrutura ficará assim:

```bash
.
├── certs
│   ├── fullchain.pem
│   ├── privkey.pem
├── config
│   ├── dynamic.yml
│   └── traefik.yml
└── compose.yml
```

## Criando arquivo de compose

No arquivo de compose, vamos subir o serviço do traefik, expondo as portas:

* 443: Aplicações web que ficarão atrás do Traefik, por exemplo o nosso Backend e o nosso Frontend
* 8080: Dashboard do Traefik (opcional)


```yaml title="compose.yaml"
---
services:
  traefik:
    image: traefik:3.2.0
    restart: always
    container_name: traefik
    ports:
      - "443:443"
      - "8080:8080"
    volumes:
      - ./config/traefik.yml:/etc/traefik/traefik.yml:ro
      - ./config/dynamic.yml:/etc/traefik/dynamic.yml:ro
      - ./certs:/etc/certs/
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - my-network

networks:
  my-network:
    external: true
```

### Arquivo ./config/traefik.yml

O arquivo `./config/traefik.yml` terá algumas configurações padrões, como o dashboard, a configuração do provider docker, etc. O mais importante é notar que criamos um `entrypoint` chamado `websecure`, escutando na porta 443:

```yaml title="./config/traefik.yml" hl_lines="7-9"
global:
  checkNewVersion: false
  sendAnonymousUsage: false
api:
  dashboard: true
  insecure: true
entrypoints:
  websecure:
    address: :443
providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
  file:
    filename: "/etc/traefik/dynamic.yml"
```

### Arquivo ./config/dynamic.yml

O arquivo `./config/dynamic.yml` serve para mapearmos os nossos certificados. Você pode incluir vários certificados para vários domínios nessa lista. Nesse caso vou criar um só, que é o certificado que assina o domínio *.brunononogaki.com. A seguir vou mostrar como gerá-lo.

```yaml title="./config/dynamic.yml"
tls:
  certificates:
    - certFile: /etc/certs/fullchain.pem
      keyFile: /etc/certs/privkey.pem
```

## Gerando certificados

Vamos usar o `certbot` para gerar certificados válidos para o nosso serviço. Instale o certbot pelo seu gerenciador de pacotes e rode o comando:

```bash
sudo certbot certonly --manual --preferred-challenges=dns --agree-tos -d brunononogaki.com -d *.brunononogaki.com
```

!!! note
    
    Esse comando vai pedir algumas valicações, como por exemplo a configuração de um TXT Record no seu DNS, para provar que o domínio é seu. Siga as etapas solicitadas.

Nesse exemplo, estou gerando certificados para os domínios brunononogaki.com e para o wildcard *.brunononogaki.com, que vai cobrir o nosso front (react.brunononogaki.com) e back (myapi.brunononogaki.com).

O certificado e a chave privada serão gerados na pasta /etc/letsencrypt/live/brunononogaki.com, com os nomes de fullchain.pem (certificado) e privkey.pem (chave privada). Copie ambos para a pasta `certs` do Traefik. Se você manter esses nomes padrões, não precisa alterar no arquivo `dynamic.yml`, mas se alterar os nomes, é preciso alterar lá também.

## Configurando o container do serviço

Pronto, agora que o Traefik está configurado, e já fazendo a tratativa dos certificados TLS, precisamos configurar os nossos serviços para utilizá-lo. Isso é feito através de `labels` nos containers. Por exemplo:

```yaml title="./infra/compose-pro.yaml" hl_lines="9-15"
services:
  web:
    container_name: django-ninja-prod
    build:
      context: ..
      dockerfile: infra/Dockerfile-pro
    env_file:
      - ../.env.production
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.myapi.rule=Host(`${BACKEND_FQDN}`)"
      - "traefik.http.routers.myapi.entrypoints=websecure"
      - "traefik.http.routers.myapi.tls=true"
      - "traefik.http.services.myapi.loadbalancer.server.port=8000"
      - "traefik.docker.network=my-network"
    networks:
      - my-network      
    depends_on:
      - database
    restart: unless-stopped
    read_only: true
    security_opt:
      - no-new-privileges:true
    tmpfs:
      - /tmp
    environment:
      - DJANGO_SETTINGS_MODULE=myapi.settings
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

Com essa configuração, estamos criando um `router` chamado **myapi**, que é encaminhado pela URL **myapi.brunononogaki.com**. Ele vai usar o `entrypoint` chamado **websecure**, que escuta na porta 443 (lembra que configuramos ele no arquivo traefik.yml?), e vai encaminhar as solicitações para a porta 8000 do container, que é onde estará rodando o Django nesse caso. E por fim, fará o uso do TLS (usando os certificados que acabamos de assinar), e estará na network **my-network**, a mesma do container do Traefik!

!!! success

    Sucesso! Temos um Traefik funcionando como Reverse Proxy para os nossos containers de back e front!