# Django Ninja Boilerplate

Repositório boilerplate para acelerar a criação de APIs REST com Django e Django Ninja.

Documentação detalhada (guia passo-a-passo):

- https://mkdocs.brunononogaki.com/outras_coisas/django_api/01_Ambiente_Poetry/

## Resumo rápido

Este README mostra como instalar, rodar localmente, executar testes e fazer deploy.

### Requisitos

- Python 3.11+ (o projeto usa `poetry`)
- Docker

### Instalação

1. Instale dependências:

```bash
poetry install
```

2. (Opcional) entre no shell do Poetry:

```bash
poetry shell
```

### Variáveis de ambiente

- Crie um arquivo de ambiente (`.env.development` ou `.env`) com pelo menos:

```
# Banco de Dados Postgres Local
DATABASE_HOST=localhost
DATABASE_PORT=5432
POSTGRES_USER=devuser
POSTGRES_PASSWORD=devpassword
POSTGRES_DB=postgres

# Variaveis da API
SECRET_KEY='mysecretkey-dev'
ALLOWED_HOSTS=localhost,127.0.0.1

# Configuração do Django
DJANGO_ADMIN_USER = 'admin'
DJANGO_ADMIN_EMAIL = 'admin@admin.com'
DJANGO_ADMIN_PASSWORD = 'devpassword'
```

### Rodando localmente

```bash
task run
# ou
poetry run task run, se não estiver com o Poetry Shell habilitado
```

O comando task run já vai subir um Banco de Dados Postgres local com Docker, então é necessário ter o Docker rodando na máquina.


### Testes, lint e formatação

- Rodar testes:

```bash
task test
# ou
poetry run task test
```

- Formatar / checar com ruff:

```bash
task format
```

### Deploy (produção)

O repositório inclui `infra/Dockerfile-pro` e `infra/compose-pro.yaml`. Use o script de deploy:

```bash
./deploy.sh up    # build + up + migrate (usa .env.production)
./deploy.sh down
```
