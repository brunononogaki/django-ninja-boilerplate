# Iniciando um projeto React para o Front-end

Precisaremos de um Front-End para consumir o nosso Backend Django Ninja. Para isso, optei por criar um projeto usando `React + Vite`. Para ficar mais fácil, deixarei o código do front nesse mesmo repositório, tudo dentro da pasta `react` na raíz do projeto.

## Construindo o ambiente

### Criando a pasta do projeto do Front-End

A primeira coisa é criar a pasta `react` na raíz do projeto, e entrar nela:
```bash
mkdir -p react
cd react
```

### Definindo a versão do Node

Eu já tenho o NVM e o Node instalados, então criaremos um arquivo na pasta react chamado `.nvmrc`, onde definiremos a versão do Node que utilizaremos:

```bash title=".nvmrc"
lts/iron

```

E agora para usar essa versão, basta dar o comando:
```bash
nvm use

Now using node v20.19.6 (npm v10.8.2)
```

### Criando o projeto com o Vite

Utilizaremos o `Vite` para construir o nosso projeto, e durante o setup, escolheremos o framework `React` com `JavaScript`. Pode dar o nome que for mais conveniente, nesse exemplo vou chamar simplesmente de `myfront`:

```bash
npm create vite@latest myfront

◆  Select a framework:
│  ○ Vanilla
│  ○ Vue
│  ● React
│  ○ Preact
│  ○ Lit
│  ○ Svelte
│  ○ Solid
│  ○ Qwik
│  ○ Angular
│  ○ Marko
│  ○ Others

◆  Select a variant:
│  ○ TypeScript
│  ○ TypeScript + React Compiler
│  ○ TypeScript + SWC
│  ● JavaScript
│  ○ JavaScript + React Compiler
│  ○ JavaScript + SWC
│  ○ React Router v7 ↗
│  ○ TanStack Router ↗
│  ○ RedwoodSDK ↗
│  ○ RSC ↗
│  ○ Vike ↗
```

Esse Wizard já vai subir o nosso front no endereço http://localhost:5173, e vai criar a seguinte estrutura de pastas dentro da pasta `react`:

```bash
.
└── myfront
    ├── README.md
    ├── eslint.config.js
    ├── index.html
    ├── package-lock.json
    ├── package.json
    ├── public
    │   └── vite.svg
    ├── src
    │   ├── App.css
    │   ├── App.jsx
    │   ├── assets
    │   │   └── react.svg
    │   ├── index.css
    │   └── main.jsx
    └── vite.config.js
```

## Criando Containers de Dev

Vamos criar um container no ambiente de dev para subir o front, e depois podemos subir ele junto com o banco de dados no comando `task run` que já temos implementado. Como por enquanto esse projeto tem o foco mais no BackEnd, acho que fica mais fácil assim. Futuramente, pode ser que a gente separe as duas coisas.

Para o ambiente de `dev`, podemos subir o React com o `npm run dev`.

Primeiro vamos criar um Dockerfile para buildar uma imagem de Node com o React:

```Dockerfile title="./react/infra/Dockerfile-dev"
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev"]
````

E agora o arquivo de compose para subir esse serviço, expondo a porta 5173 (padrão do Vite):
```yaml title="./react/infra/compose-dev.yaml"
version: "3.8"

services:
  frontend-dev:
    build:
      context: ../myfront
      dockerfile: ../infra/Dockerfile-dev
    container_name: myfront
    ports:
      - "5173:5173"
    volumes:
      - ../myfront/src:/app/src
      - ../myfront/public:/app/public
    environment:
      - REACT_APP_API_URL=http://localhost:8000
    command: npm run dev -- --host
    restart: unless-stopped    
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"    
```

E agora vamos editar o arquivo `pyproject.toml` para iniciar e baixar esses containers nos comandos de services-up, services-down e services-stop:

```toml title="./pyproject.toml" hl_lines="2-4"
[tool.taskipy.tasks]
services-up = "docker compose -f infra/compose-dev.yaml up -d && docker compose -f react/infra/compose-dev.yaml up -d"
services-stop = "docker compose -f infra/compose-dev.yaml stop && docker compose -f react/infra/compose-dev.yaml stop"
services-down = "docker compose -f infra/compose-dev.yaml down && docker compose -f react/infra/compose-dev.yaml down"
create-env-dev = "ln -sf .env.development .env"
create-env-prod = "ln -sf .env.production .env"
run = 'task create-env-dev && task services-up && python infra/wait-for-postgres.py && python manage.py migrate && python manage.py runserver'
down = "pkill -f 'manage.py runserver'; task services-down"
test = 'task create-env-dev && task services-up && python infra/wait-for-postgres.py && honcho start web test'
test-watch = 'pytest-watch'
lint = 'ruff check'
format = 'ruff format '
migrate = 'python manage.py makemigrations && python manage.py migrate'
commit = 'poetry run cz commit'
```

!!! success

    Agora quando dermos o comando `task run` no ambiente de dev, subiremos o Postgres, o Front, além de preparar o arquivo .env com o link simbólico, rodar a migração do banco e iniciar o backend na console

## Criando Containers de Prod

Para o ambiente de Produção, da mesma forma como fizemos o Backend, vamos colocar o [Traefik](../Appendix/01_Configurando_o_Traefik.md) como Reverse Proxy.

Primeiramente, vamos criar o `Dockerfile`:

```Dockerfile title="./react/infra/Dockerfile-pro"
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

RUN npm install -g serve

COPY --from=builder /app/dist ./dist

EXPOSE 3000

CMD ["serve", "-s", "dist", "-l", "3000"]

```

E agora o compose:

```yaml title="./react/infra/compose-pro.yaml"
version: "3.8"

services:
  frontend:
    build:
      context: ../myfront
      dockerfile: ../infra/Dockerfile-pro
    container_name: frontend-prod
    expose:
      - "3000"
    restart: unless-stopped
    networks:
      - my-network
    environment:
      - REACT_APP_API_URL=${REACT_APP_API_URL}
    env_file:
      - ../../.env.production
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=Host(`${FRONTEND_FQDN}`)"
      - "traefik.http.routers.frontend.entrypoints=websecure"
      - "traefik.http.routers.frontend.tls=true"
      - "traefik.http.services.frontend.loadbalancer.server.port=3000"
      - "traefik.docker.network=my-network"
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  my-network:
    external: true
```

!!! note

    O nosso container do Front ficará disponível na URL https://react.brunononogaki.com. Para mais detalhes dessa configuração do Traefik, configura esse [Apêndice](../Appendix/01_Configurando_o_Traefik.md).

## Arrumando o script de deploy

Para que o nosso workflow de deploy no Github Actions consiga subir esse container também, precisaremos editar o arquivo `./deploy.sh`:

```shell title="./deploy.sh" hl_lines="10 31-33"
#!/bin/bash

# Deploy script for production environment

set -e  # Exit on any error

if [ "$1" = "down" ]; then
  echo "🛑 Stopping and removing production containers..."
  docker compose --file infra/compose-pro.yaml down
  docker compose --file react/infra/compose-pro.yaml down
  exit 0
fi

if [ "$1" = "up" ] || [ -z "$1" ]; then
  # Default: up (build, up, migrate)
  echo "🚀 Starting production deployment..."
  
  # Check if .env.production exists
  if [ ! -f .env.production ]; then
      echo "❌ Error: .env.production file not found!"
      exit 1
  fi
  
  # Symlink .env.production to .env
  ln -sf .env.production .env
  
  # Build and start backend containers
  echo "📦 Building and starting backend..."
  docker compose --file infra/compose-pro.yaml up -d --build
  
  # Build and start frontend containers
  echo "📦 Building and starting frontend..."
  docker compose --file react/infra/compose-pro.yaml up -d --build
  
  # Run migrations inside the web container
  WEB_CONTAINER=$(docker compose --file infra/compose-pro.yaml ps -q web)
  if [ -n "$WEB_CONTAINER" ]; then
    echo "🔄 Running migrations..."
    docker compose --file infra/compose-pro.yaml exec web python manage.py migrate
  else
    echo "⚠️  Web container not found. Migration step skipped."
  fi
  
  echo "✅ Deployment complete! Backend and frontend are up and running."
  exit 0
fi

echo "Usage: $0 [up|down]"
exit 1
```
