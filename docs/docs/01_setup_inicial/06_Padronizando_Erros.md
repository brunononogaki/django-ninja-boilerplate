# Padronizando Erros e Logs

Nesse capítulo, vamos montar uma estrutura para padronizarmos os Erros e Logs no Backend. A ideia é que todas as nossas rotas de API retornarm um erro padronizado no formato JSON com a seguinte estrutura:

```json title="Formato de erro padrão"
{
  "name": "ErrorName",
  "status_code": 4XX ou 5XX,
  "message: "Detalhes do erro"
}
```

## Criando o arquivo `exceptions.py`

A implementação dos nossos erros customizados do projeto ficarão dentro do arquivo `./myapi/core/exceptions.py`. Vamos começar criando uma classe chamada `APIException`, herdando de `Exception`, para definir a nossa estrutura base dos erros, e criar uma função `exception_handler`, que define a estrutura do retorno dos erros da API.

```python title="./myapi/core/exceptions.py"
class APIException(Exception):
    """Base exception class for API errors."""

    def __init__(self, name: str, message: str, status_code: int = 500):
        self.name = name
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)
```

E agora, vou usar o decorator `exception_handler` do NinjaAPI para definir um retorno padrão dos erros, assim:

```python title="./myapi/api.py" hl_lines="9-19"
from ninja import NinjaAPI
from ninja.responses import Response

from myapi.core.exceptions import APIException

api = NinjaAPI()


@api.exception_handler(APIException)
def handle_api_exception(request, exc):
    return api.create_response(
        request,
        {
            'name': exc.name,
            'message': exc.message,
            'status_code': exc.status_code,
        },
        status=exc.status_code,
    )


api.add_router('', 'myapi.core.api.router')
```

!!! note

    Essa sugestão foi extraída dessa [issue](https://github.com/vitalik/django-ninja/issues/442) do django-ninja. Pode ser que futuramente a implementação mude, pois o problema é que o `exception_handler` pertence somente à classe `NinjaAPI`, e não à classe `Router`. Como estamos usando `Routers`, foi preciso implementar dessa forma. Senão, poderia ser feito assim: [Django Ninja - Handling errors](https://django-ninja.dev/guides/errors/)

## Criando um erro customizado e utilizando em `/status`

Agora que temos a nossa estrutura inicial montada, vamos criar um erro chamado `ServiceError`, e usá-lo na API de /status quando ocorre algum problema na conexão com o banco ou na query.

Então no arquivo `exceptions.py`, vamos definir alguns erros customizados:

```python title="./myapi/core/exceptions.py"
class APIException(Exception):
    """Base exception class for API errors."""

    def __init__(self, message: str, name: str, status_code: int = 500):
        self.name = name
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class ServiceError(APIException):
    """Raised when services fails."""

    def __init__(
        self,
        message: str = 'An unknown Service Error occured.',
        name: str = 'ServiceError',
        status_code=503
    ):
        super().__init__(message, name, status_code)
```

E agora vamos criar um try/except na função de `status`, e levantar esse erro caso ocorra alguma exceção:

```python title="./myapi/core/api.py" hl_lines="1 11 31-33"
from .exceptions import ServiceError


@router.get(
    'status',
    response=StatusSchema,
    summary='Status Check',
    description='Status check endpoint to monitor the API health.',
)
def status(request):
    try:
        with connection.cursor() as cursor:
            # Database version
            cursor.execute('SELECT version()')
            db_version = cursor.fetchone()[0]

            # Maximum number of connections
            cursor.execute('SHOW max_connections')
            max_connections = int(cursor.fetchone()[0])

            # Active connections
            cursor.execute('SELECT count(*) FROM pg_stat_activity1') # <= Forcei um erro nessa query
            active_connections = int(cursor.fetchone()[0])

        return HTTPStatus.OK, {
            'updated_at': str(datetime.now()),
            'db_version': db_version,
            'max_connections': max_connections,
            'active_connections': active_connections,
        }
    except Exception as e:
        raise ServiceError(message='Ocorreu um erro ao acessar o banco de dados ou executar uma query.')
```

!!! success

    Agora se fizermos um GET nessa rota, considerando que ela tem um erro forçado na query, o retorno será esse:

    ```json
    {
      "name": "ServiceError",
      "message": "Ocorreu um erro ao acessar o banco de dados ou executar uma query.",
      "status_code": 503
    }
    ```

## Incluindo Logs na console

Para incluir os logs na console do nosso servidor, e ficar mais fácil de fazer troubleshootings, vamos incluir a biblioteca `loguru`:

```bash
poetry add loguru
```

E para incluir esses logs, vamos apenas importar a biblioteca, e logar uma mensagem do tipo `error`:

```python title="./myapi/core/api.py" hl_lines="1 32"
from loguru import logger


@router.get(
    'status',
    response=StatusSchema,
    summary='Status Check',
    description='Status check endpoint to monitor the API health.',
)
def status(request):
    try:
        with connection.cursor() as cursor:
            # Database version
            cursor.execute('SELECT version()')
            db_version = cursor.fetchone()[0]

            # Maximum number of connections
            cursor.execute('SHOW max_connections')
            max_connections = int(cursor.fetchone()[0])

            # Active connections
            cursor.execute('SELECT count(*) FROM pg_stat_activity1') # <= Forcei um erro nessa query
            active_connections = int(cursor.fetchone()[0])

        return HTTPStatus.OK, {
            'updated_at': str(datetime.now()),
            'db_version': db_version,
            'max_connections': max_connections,
            'active_connections': active_connections,
        }
    except Exception as e:
        logger.error(f"Database Error: {e}")
        raise ServiceError(message='Ocorreu um erro ao acessar o banco de dados ou executar uma query.')
```

Na console do servidor, o erro logado será assim:

```bash
2025-12-15 10:40:05.522 | ERROR    | myapi.core.api:status:57 - Database Error: relation "pg_stat_activity1" does not exist
LINE 1: SELECT count(*) FROM pg_stat_activity1
```

## Incluindo demais erros customizados

Agora vamos criar alguns outros erros customizados no arquivo `exceptions.py`, e aplicá-lo nas demais APIs:

```python title="./myapi/core/exceptions.py"
from ninja.responses import Response


class APIException(Exception):
    """Base exception class for API errors."""

    def __init__(self, message: str, name: str, status_code: int = 500):
        self.name = name
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ServiceError(APIException):
    """Raised when services fails."""

    def __init__(
        self,
        message: str = 'An unknown Service Error occurred.',
        name: str = 'ServiceError',
        status_code: int = 503
    ):
        super().__init__(message, name, status_code)


class ValidationError(APIException):
    """Raised when validation fails."""

    def __init__(
        self,
        message: str = 'Validation error occurred.',
        name: str = 'ValidationError',
        status_code: int = 400
    ):
        super().__init__(message, name, status_code)


class NotFoundError(APIException):
    """Raised when resource is not found."""

    def __init__(
        self,
        message: str = 'Resource not found.',
        name: str = 'NotFoundError',
        status_code: int = 404
    ):
        super().__init__(message, name, status_code)


class ConflictError(APIException):
    """Raised when resource already exists."""

    def __init__(
        self,
        message: str = 'Resource already exists.',
        name: str = 'ConflictError',
        status_code: int = 409
    ):
        super().__init__(message, name, status_code)


class UnauthorizedError(APIException):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = 'Invalid credentials.',
        name: str = 'UnauthorizedError',
        status_code: int = 401
    ):
        super().__init__(message, name, status_code)
```

Futuramente, quando implementarmos por exemplo o endpoint de `/users`, usaremos esses erros da seguinte forma:

```python title="./myapi/users/api.py" hl_lines="6-9"
@router.post(
    'users', response=UserWithGroupsSchema, summary='Create user', description='Create a new user', auth=AdminAuth()
)
def create_users(request, data: UserCreateSchema):
    # Pre-create validation: check username and email uniqueness
    if User.objects.filter(username=data.username).exists():
        raise ConflictError('Username already exists')
    if User.objects.filter(email=data.email).exists():
        raise ConflictError('Email already exists')

    user = User.objects.create_user(
        username=data.username,
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        password=data.password,
    )

    return Response(UserWithGroupsSchema.from_orm(user), status=201)
```

## Erros de 404: Not found

Para os erros de `404: Not Found`, o Django possui um método padrão `get_object_or_404`, mas ele lança uma exceção `Http404` que não passa pelo nosso exception_handler customizado. Então temos duas opções: uma é registrar um `exception handler` para o `Http404`, que serviria para todos os erros 404 que utilizam o método `get_object_or_404` do Django:

```python title="./myapi/api.py"
from django.http import Http404

@api.exception_handler(Http404)
def handle_not_found(request, exc):
    return Response(
        {
            'name': 'NotFoundError',
            'message': 'Resource not found',
            'status_code': 404,
        },
        status=404
    )
```

Mas para termos maior controle, prefiro deixarmos de usar o `get_object_or_404` e passar a usar try/excepts normais. Por exemplo, na rota de DELETE de Users (implementação futura):

```python title="./myapi/users/api.py"
@router.delete(
    'users/{id}', summary='Delete user', response={204: None}, description='Delete an user', auth=OwnerOrAdminAuth()
)
def delete_user(request, id: uuid.UUID):
    # user = get_object_or_404(User, id=id) <= Deixar de usar assim
    try:
        user = User.objects.get(id=id)
    except User.DoesNotExist:
        raise NotFoundError('User not found')

    user.delete()
    return Response(None, status=204)
```

!!! success

    Agora temos implementado um tratamento de erros customizado, padronização nos retornos da API, e logging usando o `loguru`.