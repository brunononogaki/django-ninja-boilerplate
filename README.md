# Django Ninja Boilerplate

This project is a boilerplate for building REST APIs using Django and Django Ninja.

## Step-by-step deployment from scratch

This is a step-by-step deployment so you can build this structure without cloning this repo. This is for reference only, you can just clone the repository if you want.

1. Create a Django Project
```bash
poetry new django-ninja-boilerplate
```

2. Install Dependencies
```
poetry add django-ninja
poetry add django-extensions
poetry add python-decouple
```

3. Edit `pyproject.toml` file:
```toml
[tool.poetry]
package-mode = false
```

4. Start poetry shell (optional)
```
poetry shell
```

5. Create a new Django Project
```
django-admin startproject myapi .

# If not using poetry shell, run this command as:
poetry run django-admin startproject myapi .
```

5. Navigate to `myapi` folder, and create a new app named `core` from there. It will make the app folders to be placed inside the main `myapi` folder.

```bash
cd myapi
python ../manage.py startapp core
```

6. Create a `.env` file into the root directory
```
# .env file
SECRET_KEY=my-super-secret-key
```

7. Edit `myapi/settings.py`
```python
from decouple import config
SECRET_KEY = config('SECRET_KEY') # <= Get the SECRET_KEY from .env file using the lib decouple

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions', # <= add this
    'myapi.core', # <= add this
]
```

8. Edit `myapi/core/apps.py`
```python
class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myapi.core' # <= change this
```

9. Create a file named `myapi/api.py`:
```python
from ninja import NinjaAPI

api = NinjaAPI()

api.add_router('', 'myapi.core.api.router')
```

10. Edit the main `myapi/urls.py` file, importing api and creating the api routes:
```python
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

11. Create a file named `myapi/core/schemas.py`:
```python
from ninja import Schema


class StatusSchema(Schema):
    status: str
```


12. Create a file named `myapi/core/api.py`:
```python
from http import HTTPStatus
from ninja import Router

from .schemas import StatusSchema


router = Router(tags=['Core'])


@router.get(
    'healthcheck',
    response=StatusSchema,
    tags=['Health Check'],
    summary='Health Check Summary',
    description='Verificação de status que permite monitorar a saúde da API.'
)
def healthcheck(request):
    return HTTPStatus.OK, {'status': 'ok'}
```

13. Create migrations and start the server
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

14. Access your application: `http://localhost:8000/`

15. From now you can keep developing new apps, with their respective models, schemas, tests, etc.


## Adding Postgres Database

Follow these steps to have this backend communicating with a PostgreSQL for Dev

1. Create a file named `infra/compose.yaml`
```yaml
services:
  database:
    container_name: postgres-dev
    image: postgres:16.0-alpine3.18
    env_file:
      - ../.env.development
    ports:
      - "5432:5432"
    restart: unless-stopped    
```

2. Create a file `.env.development` in the root directory:
```
DATABASE_HOST=localhost
DATABASE_PORT=5432
POSTGRES_USER=devuser
POSTGRES_PASSWORD=devpassword
POSTGRES_DB=postgres
```

3. Add `psycopg` library
```
poetry add psycopg
````

4. Edit `myapi/settings.py`:
```python
# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }
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

5. Run migrations
```
python manage.py migrate
```