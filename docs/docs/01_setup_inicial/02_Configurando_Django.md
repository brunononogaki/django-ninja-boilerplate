# Configurando o Django

Agora que já temos a nossa infra toda configurada, vamos começar a subir o Django e criar a nossa primeira rota de API!

## Criando a app `core`:

Para começar a nossa API, vamos criar uma app nova chamada `core`, que vai ter coisas relacionadas ao sistema, como API de check de status e de autenticação. Posteriormente criaremos outras apps para a nossa API.

Para a estrutura de pastas das apps ficarem dentro da pasta do projeto "myapi˜, vamos primeiro dar um cd no "myapi" e criar o app a partir de lá. Desse jeito, acho que fica mais organizado:

```bash
cd myapi
python ../manage.py startapp core
```

Na raíz do projeto vai ter as pastas `src` e `tests`, que o Django cria por padrão. Podemos apagá-las para não ficar lixo.

A estrutura de pastas do projeto ficará assim:

```bash
.
├── db.sqlite3
├── infra
│   ├── compose-dev.yaml
│   └── wait-for-postgres.py
├── manage.py
├── myapi
│   ├── __init__.py
│   ├── asgi.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── migrations
│   │   │   └── __init__.py
│   │   ├── models.py
│   │   ├── tests.py
│   │   └── views.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── poetry.lock
├── Procfile
├── pyproject.toml
├── pytest.ini
├── README.md
```

## Editando o `./myapi/core/apps.py` e `./myapi/settings.py`

Vamos editar o arquivo `./myapi/core/apps.py` para o seguinte:

```python title="./myapi/core/apps.py" hl_lines="4"
class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # name = 'core'        # ==> Remover
    name = 'myapi.core'    # <== Adicionar
```

E agora no `./myapi/settings.py`, vamos incluir o seguinte:

- Tirar a SECRET_KEY do `settings.py` e importar o `.env` através da lib `decouple`
- Adicionar ALLOWED_HOSTS já com o domínio que futuramente colocaremos pra nossa Prod
- Adicionar a nossa app `core` em `INSTALLED_APPS`, junto com a extensão `django_extensions`, que poderemos usar mais pra frente
- Configurar o Banco de Dados Postgres ao invés do SQLIte

```python title="./myapi/settings.py" hl_lines="12-13"
from decouple import Csv, config

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',   # <= Adicione isso
    'myapi.core',          # <= Adicione isso
]

# Remova esse bloco:
#DATABASES = {
#    'default': {
#        'ENGINE': 'django.db.backends.sqlite3',
#        'NAME': BASE_DIR / 'db.sqlite3',
#    }
#}
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB', default='postgres'),
        'USER': config('POSTGRES_USER', default='devuser'),
        'PASSWORD': config('POSTGRES_PASSWORD', default='devpassword'),
        'HOST': config('DATABASE_HOST', default='localhost'),
        'PORT': config('DATABASE_PORT', default='5432'),
    }
}
```

## Criando `./myapi/api.py`:

Vamos criar um arquivo novo chamado `./myapi/api.py`. Esse será o arquivo principal da nossa API, que vai agrupar as rotas dos demais apps, como as do `core`:

```python title="./myapi/api.py"
from ninja import NinjaAPI

api = NinjaAPI()

api.add_router('', 'myapi.core.api.router')
```

## Editando `./myapi/urls.py`:

Agora vamos editar o `./myapi/urls.py`, adicionando a rota principal da nossa API, que vou chamar de `api/v1/`:

```python title="./myapi/urls.py"
from django.contrib import admin
from django.urls import path

from .api import api

urlpatterns = [
    path('admin/', admin.site.urls),
]

api_urlpatterns = [
    path('api/v1/', api.urls),
]

urlpatterns += api_urlpatterns
```

!!! success

    Django configurado, vamos começar a criar os nossos primeiros endpoints!