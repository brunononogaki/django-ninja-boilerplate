# Implementando CD/CD

Por enquanto o nosso sistema ainda não tem muita coisa produtiva, mas já temos a estrutura do projeto e uma rota para conferir o status da aplicação. Nesse capítulo, vamos implementar o CI/CD nesse projeto através de Workflows do GitHub Action. A ideia é que ao fazer um Pull Request para a branch `main`, o Workflow será chamado para:

- Executar os testes
- Rodar o Linter com o Ruff
- Fazer deploy no servidor

!!! note

    Nesse exemplo, vou subir a aplicação toda em uma VPS da Hostinger. Nesse ambiente, eu já tenho um container de Traefik configurado, que vou deixar documentando nesse [apêndice](../Appendix/01_Configurando_o_Traefik.md).

    O Traefik vai servir como um Reverse Proxy, encaminhando as solicitações HTTPS dos clients para esse container. E por fins de exemplos, implementaremos esse Backend na URL https://myapi.brunononogaki.com.

## Criando Workflow de Testes

Como já temos os nossos testes automatizados rolando no projeto, basta criarmos um Workflow para executá-los. Esses workflows são colocados em uma pasta especial chamada `.github`, na raíz do projeto, dentro de um subdiretório chamado 'Workflows'. Vamos primeiro criar essa estrutura:

```bash
mkdir -p .github/workflows
```

Agora dentro dessa pasta, vamos criar o arquivo `tests.yaml`

```yaml title="./.github/workflows/tests.yaml"
name: Automated Tests

on: pull_request

jobs:
  pytest:
    name: pytest
    runs-on: ubuntu-latest

    steps:
      - name: "Download code"
        uses: actions/checkout@v4

      - name: "Install Python 3.13"
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: "Install Poetry"
        run: pipx install poetry

      - name: "Install dependencies"
        run: poetry install

      - name: "Run tests"
        run: poetry run task test
```

!!! note

    É importante termos o arquivo .env.development no repositório, porque o nosso script do `task test` utiliza ele para criar um link simbólico para o .env.

Agora, se a gente criar uma nova branch, commitar esse arquivo, fazer um git pull, e depois um Pull Request, esse job será chamado.

```bash
git checkout -b "action/tests"
git add .
git commit -m "Adding tests workflow"
git push --set-upstream origin actions/tests
```

![alt text](static/test-workflow.png)

!!! warning

    Caso os testes falhem, ainda assim o GitHub vai permitir fazermos o merge para a main. O ideal seria isso não ser possível, pois não queremos subir um código quebrado. Para isso, vamos nos Settings do nosso projeto, e navegar nas seguintes opções (pode ser que a interface mude no futuro, mas a ideia é essa):

    * Settings --> Branches --> Add Branch ruleset
    * Crie um nome para o ruleset, por exemplo: branch-main-protection
    * Mude para `Enabled`
    * Em `Target branches`, clique em Add target e selecione `Include default branch`
    * Marque as opções:
      * Restrict deletions
      * Require a pull request before merging
      * Require status checks to pass
        * Adicione o check `pytest`
      * Block force pushes

## Criando o Workflow de Lint

O Workflow de Linting será o mesmo padrão, porque já temos o comando `task link` no nosso arquivo `pyproject.toml`. Então basta criar esse novo Workflow, subir para o repositório, e configurar esse job nas configurações do `Require status checks to pass`, para assim impedir que alguém faça um merge para a main sem rodar o `ruff`.

```yaml title="./.github/workflows/lint.yaml"
name: Linting

on: pull_request

jobs:
  pytest:
    name: ruff
    runs-on: ubuntu-latest

    steps:
      - name: "Download code"
        uses: actions/checkout@v4

      - name: "Install Python 3.13"
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: "Install Poetry"
        run: pipx install poetry

      - name: "Install dependencies"
        run: poetry install

      - name: "Run linting"
        run: poetry run task lint
```

![alt text](static/lint-workflow.png)

!!! warning

    Ops, veja agora que o linter falhou, e com isso a gente não consegue fazer o merge na branch `main`!
    Mas vou corrigir isso pelo VSCode mesmo, vendo erro por erro e atacando a resolução. Por isso é importante fazer isso logo no começo do projeto, para não acumular muita coisa para consertar. O Copilot ou alguma outra IA podem te dar uma boa mão na resolução desses problemas

## Criando os Scripts para Deployment em Produção

Vamos preparar a infraestrutura para o Deployment em produção. Criaremos basicamente um `compose-pro.yaml` para subir os containers de Prod, e um Dockerfile para criarmos uma imagem do nosso WebServer de Prod usando `uvicorn`, ao invés de subir com o `python manage.py runserver`, que é destinado apenas para desenvolvimento.

Além disso, vamos criar também um script `deploy.sh` pra ficar mais fácil de subir tudo.

Começando com o arquivo do docker-compose, vamos declarar dois containers:

- Um container de Postgres, com a diferença que aqui em Prod temos que mapear o volume para os dados persistirem caso ele reinicie. E aqui não vamos expor nenhuma porta, porque o nosso servidor web vai conseguir falar internamente através da network do docker.
- Um container do nosso Web Server Django, configurado para utilizar o Traefik como Reverse proxy, escutando na URL **myapi.brunononogaki.com**, porta 443 (HTTPS), e encaminhando para a porta 8000 do container.

```yaml title="./infra/compose-pro.yaml"
version: "3.9"

services:
  database:
    container_name: postgres-prod
    image: postgres:17.0
    env_file:
      - ../.env.production
    restart: unless-stopped
    volumes:
      - pgdata:/var/lib/postgresql/data
    networks:
      - my-network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  web:
    container_name: django-ninja-prod
    build:
      context: ..
      dockerfile: infra/Dockerfile-pro
    env_file:
      - ../.env.production
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.myapi.rule=Host(`${BACKEND_URL}`)"
      - "traefik.http.routers.myapi.entrypoints=websecure"
      - "traefik.http.routers.myapi.tls=true"
      - "traefik.http.services.myapi.loadbalancer.server.port=8000"
      - "traefik.docker.network=my-network"
    networks:
      - my-network
    depends_on:
      - database
    restart: unless-stopped
    volumes:
      - ../:/app
    environment:
      - DJANGO_SETTINGS_MODULE=myapi.settings
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  pgdata:

networks:
  my-network:
    external: true
```

E o `Dockerfile-pro` ficará assim:

```Dockerfile title="./infra/Dockerfile-pro"
FROM python:3.13-slim


# Install system dependencies
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app


 # Copy only dependency files for faster cache install
COPY pyproject.toml poetry.lock ./
RUN pip install --no-cache-dir poetry && poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --only main

# Copy the rest of the code
COPY . .

# Expose Uvicorn port
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "myapi.asgi:application", "--host", "0.0.0.0", "--port", "8000"]
```

Agora se dermos um `docker compose --file infra/compose-pro.yaml up -d`, os dois containers irão subir. Mas para ficar mais fácil depois na hora de criarmos o nosso Workflow do GitHub Actions, vamos criar um arquivo `deploy.sh`, com permissão de execução. Outra coisa que o script vai fazer também é criar o link simbólico do arquivo `.env.production` para `.env`. Assim, não precisamos fazer nada disso no script do Workflow.

```shell title="./deploy.sh"
#!/bin/bash

# Deploy script for production environment

set -e  # Exit on any error

if [ "$1" = "down" ]; then
  echo "🛑 Stopping and removing production containers..."
  docker compose --file infra/compose-pro.yaml down
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
  # Build and start containers
  docker compose --env-file .env.production --file infra/compose-pro.yaml --project-name django-ninja up -d --build
  # Run migrations inside the web container
  WEB_CONTAINER=$(docker compose --file infra/compose-pro.yaml ps -q web)
  if [ -n "$WEB_CONTAINER" ]; then
    docker compose --file infra/compose-pro.yaml exec web python manage.py migrate
  else
    echo "Web container not found. Migration step skipped."
  fi
  echo "✅ Deployment complete! Containers are up and migrations applied."
  exit 0
fi

echo "Usage: $0 [up|down]"
exit 1
```

!!! success

    Pronto! Agora, em teoria, se você acessar o servidor manualmente, criar um arquivo `.env.production` lá dentro com os dados do seu ambiente, e rodar um `./deploy.sh`, o serviço de banco e web deverão subir com sucesso!

## Criando o Workflow de Deploy na VPS da Hostinger

E agora vamos criar o nosso workflow de Deploy em uma VPS da Hostinger. Eis o que iremos precisar:

- IP do servidor na Hostinger
- Usuário
- Chave SSH
- Diretório no servidor onde colocarmos o código

!!! tip

    Para gerar uma chave SSH para um usuário, você pode fazer o seguinte:
    ```bash
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/vps_key
    
    <IP_SERVIDOR>
    ```
    Nessa pasta serão criados os arquivos vps_key (chave privada) e vps_key.pub (chave pública). A chave pública foi copiada para dentro do servidor, e a chave privada é o que usaremos para criar as Secrets no GitHub para autenticação no servidor.

Com posse dessas informações, vamos criar as SECRETS dentro do nosso repositório no GitHub.

- No repositório no GitHub, vá em `Settings`
- Vá para o menu `Secrets and variables` -> `Actions`
- Clique em `New repository secret`, e crie as seguintes variáveis:
  - DEPLOY_HOST: IP do seu servidor
  - DEPLOY_USER: Usuário para logar no servidor. Nesse caso, usaremos o `root` mesmo, pois é só um lab.
  - DEPLOY_SSH_KEY: Conteúdo da Chave Privada gerada anteriormente
  - DEPLOY_PORT: 22, que é a porta padrão do SSH. Mas caso o seu servidor escute por outra porta, é só ajustar
  - DEPLOY_PATH: /root/django-ninja-boilerplate, ou o diretório que você deseja colocar o código no servidor

Vai ficar assim:

![alt text](static/github-secrets.png)

E agora vamos criar o nosso workflow de deploy, com a diferença que não chamaremos ele nos pull requests, mas sim quando houver algum push na branch main. E usaremos as actions `rsync-deployments` para copiar o código do repo para o servidor, e o `ssh-action` para rodar o script de deploy.

```yaml title="./.github/workflows/deploy.yaml"
name: Deploy to VPS

on:
  push:
    branches:
      - main

jobs:
  deploy:
    name: Deploy to Server
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Sync code to server
        uses: burnett01/rsync-deployments@7.1.0
        with:
          switches: -avz --delete --exclude='.git*' --exclude='.env.production'
          path: ./
          remote_path: ${{ secrets.DEPLOY_PATH }}
          remote_host: ${{ secrets.DEPLOY_HOST }}
          remote_user: ${{ secrets.DEPLOY_USER }}
          remote_key: ${{ secrets.DEPLOY_SSH_KEY }}
          remote_port: ${{ secrets.DEPLOY_PORT || 22 }}

      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_SSH_KEY }}
          port: ${{ secrets.DEPLOY_PORT || 22 }}
          script: |
            set -e
            cd ${{ secrets.DEPLOY_PATH }}
            echo "Chamando o script de deploy"
            ./deploy.sh
```

!!! tip

    A primeira execução desse Workflow vai falhar, porque não temos o arquivo `.env.production` criado. Então quando ele rodar pela primeira vez e criar a pasta com o projeto, acesse o servidor e crie o arquivo `.env.production` manualmente. A partir disso, o workflow vai funcionar, porque no setp de `Sync code to server`, estamos excluindo do rsync o arquivo .env.production, para que ele não seja removido.

Agora, quando você fizer um push para a branch main, os containers do WebServer e do Banco de Dados irão subir:

```bash
CONTAINER ID   IMAGE                    COMMAND                  CREATED         STATUS                 PORTS                                                                                          NAMES
60055a3d99e3   infra-web                "uvicorn myapi.asgi:…"   50 minutes ago   Up 50 minutes         8000/tcp                                                                                       django-ninja-prod
056561459f60   postgres:17.0            "docker-entrypoint.s…"   6 seconds ago   Up 6 seconds           5432/tcp                                                                                       postgres-prod
```

!!! tip

    Em produção, o Django não serve arquivos estáticos automaticamente, então a interface do `/admin` ficará sem a formatação do CSS e sem as imagens. Para resolver isso, precisamos rodar um `python manage.py collectstatic` no `Dockerfile-pro`, e a forma mais simples de servir esses arquivos é instalando uma lib chamada `Whitenoise`:

    ```bash
    poetry add whitenoise
    ```

    E no `settings.py` vamos adicionar isso:
    ```python title="./myapi/settings.py"
    STATIC_ROOT = BASE_DIR / 'staticfiles'

    # WhiteNoise configuration
    WHITENOISE_AUTOREFRESH = DEBUG
    WHITENOISE_USE_FINDERS = True
    WHITENOISE_MIMETYPES = {
        '.woff2': 'font/woff2',
        '.woff': 'font/woff',
        '.ttf': 'font/ttf',
    }

    MIDDLEWARE = [
    # Add this:
    'whitenoise.middleware.WhiteNoiseMiddleware',
    ]
    ```

    Por fim, no `Dockerfile-pro`, adicionaremos isso antes do `EXPOSE 8000`:
    ```
    # Collect static files
    RUN python manage.py collectstatic --noinput
    ```
    


## Adicionando Scans de Segurança

Com o pipeline funcionando, vamos adicionar uma camada de segurança automática em cada Pull Request. Usaremos três ferramentas complementares:

| Ferramenta | O que analisa | Configuração |
|---|---|---|
| **Trivy** | CVEs em dependências e na imagem Docker | Workflow no repositório |
| **Semgrep** | Vulnerabilidades no código-fonte (SAST) | GitHub App (portal) |
| **SonarCloud** | Qualidade e security hotspots no código | GitHub App (portal) |

### Trivy

O [Trivy](https://trivy.dev/) verifica CVEs em dependências Python (`poetry.lock`), pacotes da imagem Docker, e secrets acidentalmente commitados.

Antes de criar o workflow, atualize o `Dockerfile-pro` para usar um build multi-stage. Isso reduz drasticamente o número de CVEs na imagem final, porque o stage de build (que precisa de `build-essential`, `gcc`, etc.) é descartado — apenas as libs necessárias em runtime são copiadas:

```Dockerfile title="./infra/Dockerfile-pro"
FROM python:3.13-slim AS builder

RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN pip install --no-cache-dir poetry && poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --only main


FROM python:3.13-slim

RUN apt-get update && apt-get install -y libpq5 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn

COPY . .

RUN SECRET_KEY=django-insecure-collectstatic-build-only python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["uvicorn", "myapi.asgi:application", "--host", "0.0.0.0", "--port", "8000"]
```

!!! note

    O `collectstatic` precisa da variável `SECRET_KEY` setada para o Django inicializar, mas não usa o valor para nada criptográfico. Por isso usamos um dummy com o prefixo `django-insecure-` diretamente no `RUN`, sem expor nenhum segredo real na imagem. A `SECRET_KEY` de produção é injetada em runtime via `env_file`.

Agora crie o workflow:

```yaml title="./.github/workflows/trivy.yaml"
name: Trivy Security Scan

on: pull_request

jobs:
  trivy:
    name: trivy
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Scan dependencies (poetry.lock)
        uses: aquasecurity/trivy-action@314ff8b43182423b84c50b1670b0e10f858f2d98
        with:
          scan-type: fs
          scan-ref: .
          scanners: vuln,secret
          severity: CRITICAL,HIGH
          exit-code: 1
          ignore-unfixed: true
          skip-dirs: myapi/core/tests,myapi/users/tests

      - name: Build Docker image
        run: docker build -f infra/Dockerfile-pro -t myapi:pr .

      - name: Scan Docker image
        uses: aquasecurity/trivy-action@314ff8b43182423b84c50b1670b0e10f858f2d98
        with:
          scan-type: image
          image-ref: myapi:pr
          severity: CRITICAL,HIGH
          exit-code: 1
          ignore-unfixed: true
```

Decisões importantes:

- **`ignore-unfixed: true`** — o workflow só falha quando existe uma versão corrigida disponível. CVEs sem fix (dependências transitivas do SO sem patch publicado) não bloqueiam o build, já que não há nenhuma ação possível.
- **SHA completo no `uses`** — em vez de `@master`, usamos o SHA completo do commit. Isso evita supply chain attacks onde uma tag mutável poderia apontar para código malicioso.
- **`skip-dirs`** — os diretórios de teste são excluídos do scan de secrets para evitar falsos positivos em fixtures e dados de teste.

### Semgrep

O [Semgrep](https://semgrep.dev/) faz análise estática (SAST) do código-fonte, identificando vulnerabilidades como SQL injection, XSS, uso inseguro de funções, e padrões problemáticos específicos de Django.

A integração com o GitHub é feita diretamente pelo portal, sem necessidade de adicionar um workflow ao repositório:

1. Acesse [semgrep.dev](https://semgrep.dev) e crie uma conta
2. Vá em **Settings → Source Code Managers** e conecte sua conta do GitHub
3. Selecione o repositório desejado
4. O Semgrep vai automaticamente criar um check em cada Pull Request

A partir daí, a cada PR o Semgrep roda as regras do ruleset configurado (o `p/django` já cobre os principais vetores de ataque para projetos Django) e reporta os findings diretamente na interface do GitHub.

### SonarCloud

O [SonarCloud](https://sonarcloud.io) analisa qualidade de código e security hotspots — padrões que merecem revisão manual por terem potencial de risco (uso de `eval`, configurações inseguras, etc.) — além de duplicação de código e cobertura de testes.

Assim como o Semgrep, a configuração é feita pelo portal:

1. Acesse [sonarcloud.io](https://sonarcloud.io) e faça login com sua conta do GitHub
2. Clique em **+** → **Analyze new project** e selecione o repositório
3. Escolha o método de análise **Automatic Analysis**
4. O SonarCloud vai criar um check automático em cada Pull Request

!!! tip

    O SonarCloud classifica os findings em **Bugs**, **Vulnerabilities**, **Code Smells** e **Security Hotspots**. Os Hotspots não são necessariamente vulnerabilidades — eles precisam de revisão humana para determinar se representam risco real no contexto do projeto. Você pode marcá-los como **Safe** ou **Fixed** diretamente no portal.

### Adicionando os checks como obrigatórios

Por fim, adicione os três como status checks obrigatórios no GitHub:

- Settings → Branches → branch-main-protection → Require status checks to pass
    - Adicione os checks: `trivy`, `Semgrep OSS Scan`, `SonarCloud Code Analysis`

!!! success

    Sucesso!!! Nosso CI/CD ta prontinho, com testes automatizados, scan de segurança e deploy para produção!
