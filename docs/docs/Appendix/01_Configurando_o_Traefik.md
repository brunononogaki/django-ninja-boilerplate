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

Criarei uma pasta chamada `traefik`, com a seguinte estrutura:

```bash
.
├── certs
│   └── acme.json
├── config
│   ├── dynamic.yml
│   └── traefik.yml
└── docker-compose.yml
```

A pasta `certs` armazena o `acme.json`, que é onde o Traefik persiste os certificados gerenciados pelo Let's Encrypt. Crie o arquivo com as permissões corretas antes de subir o container:

```bash
mkdir -p certs
touch certs/acme.json
chmod 600 certs/acme.json
```

!!! warning
    O `chmod 600` é obrigatório. O Traefik rejeita o arquivo se ele tiver permissões abertas, pois contém chaves privadas dos certificados.

## Criando arquivo de compose

No arquivo de compose, vamos subir o serviço do Traefik expondo as portas:

* **80**: Necessária para o desafio HTTP do Let's Encrypt e para o redirect HTTP → HTTPS
* **443**: Tráfego HTTPS das aplicações
* **8080**: Dashboard do Traefik (opcional)

```yaml title="docker-compose.yml"
---
services:
  traefik:
    image: traefik:3.6.9
    restart: always
    container_name: traefik
    ports:
      - "80:80"
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

O `traefik.yml` contém as configurações estáticas do Traefik. Os pontos principais são:

- Dois entrypoints: `web` (porta 80) com redirect automático para HTTPS, e `websecure` (porta 443)
- O bloco `certificatesResolvers` que configura o cliente ACME nativo do Traefik para solicitar e renovar certificados Let's Encrypt automaticamente via desafio HTTP

```yaml title="./config/traefik.yml" hl_lines="7-14 22-28"
global:
  checkNewVersion: false
  sendAnonymousUsage: false
api:
  dashboard: true
  insecure: true
entrypoints:
  web:
    address: :80
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
  websecure:
    address: :443
providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
  file:
    filename: "/etc/traefik/dynamic.yml"
certificatesResolvers:
  letsencrypt:
    acme:
      email: seu@email.com
      storage: /etc/certs/acme.json
      httpChallenge:
        entryPoint: web
```

!!! note "Como funciona a renovação automática"
    Quando um container sobe com a label `tls.certresolver=letsencrypt`, o Traefik detecta o domínio, solicita um certificado ao Let's Encrypt e resolve o desafio: o Let's Encrypt faz uma requisição HTTP na porta 80 do servidor, o Traefik responde, e o certificado é emitido e salvo no `acme.json`. A renovação acontece automaticamente antes do vencimento — sem intervenção manual, sem cron job, sem certbot.

### Arquivo ./config/dynamic.yml

O `dynamic.yml` serve para configurações dinâmicas adicionais (middlewares, rotas customizadas, etc.). Com o ACME ativo, não é mais necessário declarar certificados manualmente aqui:

```yaml title="./config/dynamic.yml"
# Certificados gerenciados automaticamente pelo ACME (Let's Encrypt) via Traefik
```

## Configurando o container do serviço

Com o Traefik configurado, basta adicionar `labels` nos containers das aplicações. A label `tls.certresolver=letsencrypt` instrui o Traefik a obter e renovar o certificado para aquele domínio:

```yaml title="./infra/compose-pro.yaml" hl_lines="9-16"
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
      - "traefik.http.routers.myapi.tls.certresolver=letsencrypt"
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

Com essa configuração, o router **myapi** responde pela URL definida em `BACKEND_FQDN`, escuta na porta 443 via entrypoint `websecure`, encaminha as requisições para a porta 8000 do container (onde roda o Django), e delega ao Traefik o gerenciamento completo do certificado TLS.

!!! success

    Sucesso! Temos um Traefik funcionando como Reverse Proxy com certificados TLS emitidos e renovados automaticamente pelo Let's Encrypt!
