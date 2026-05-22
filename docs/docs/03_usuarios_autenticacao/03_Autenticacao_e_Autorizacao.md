# Implementando Autenticação e Autorização

Então até agora temos os nossos CRUDs de usuários criados, assim como a rota para ativar uma conta através de um Activation Token, mas no momenton não temos como fazer o login, e qualquer pessoa anônima (não logada) pode listar, criar, alterar e deletar dados da tabela. A ideia é começarmos a proteger essas rotas.

## Autenticação JWT

Vamos implantar a autenticação da API por meio de tokens JWT. Para isso, vamos instalar o `PyJWT`

```bash
poetry add PyJWT
```

!!! note

    Toda a API de autenticação será criada dentro da app `core`, que criamos no começo do projeto, e que até agora só tinha a rota de `/status`.

Agora vamos criar um arquivo em `./myapi/core/auth.py`, para colocar a função de criação do token, usando a lib `jwt`.

```python title="./myapi/core/auth.py"
import jwt
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from ninja.security import HttpBearer

User = get_user_model()
ALGO = 'HS256'
ACCESS_LIFETIME = timedelta(minutes=15)
REFRESH_LIFETIME = timedelta(days=30)


def create_token(user):
    now = datetime.utcnow()
    access_token = jwt.encode(
        {'user_id': str(user.id), 'exp': now + ACCESS_LIFETIME, 'type': 'access'},
        settings.SECRET_KEY,
        algorithm=ALGO,
    )
    refresh_token = jwt.encode(
        {'user_id': str(user.id), 'exp': now + REFRESH_LIFETIME, 'type': 'refresh'},
        settings.SECRET_KEY,
        algorithm=ALGO,
    )
    return {'access_token': access_token, 'refresh_token': refresh_token}
```

Agora precisamos criar a rota de geração de Token (`/login`). Mas antes, vamos criar os schemas para o recebimento e retorno dessa rota, e para esse cenário, esperamos receber um username e password, e retornar um access_token e um refresh_token, que poderá ser usado para renovar o access token antes de ele expirar.

```python title="./myapi/core/schemas.py"
class LoginRequest(Schema):
    username: str
    password: str


class TokenResponse(Schema):
    access_token: str
    refresh_token: str | None = None
    token_type: str = 'bearer'
```

Agora sim vamos criar a rota de `/login`:

```python title="./myapi/core/api.py" hl_lines="6-7"
from django.contrib.auth import get_user_model, authenticate
from .auth import create_token

from .schemas import (
    StatusSchema,
    TokenResponse,  #<= Adicione isso
)

@router.post('login', tags=['Auth'], response=TokenResponse)
def login(request, credentials: LoginRequest):
    user = authenticate(username=credentials.username, password=credentials.password)
    if not user:
        logger.warning(f'Failed login attempt for username: {credentials.username}')
        raise UnauthorizedError()
    logger.info(f'User {user.username} (id={user.id}) logged in')
    tokens = create_token(user)
    return 200, {'token_type': 'bearer', **tokens}
```

!!! success

    Agora temos um novo endpoint `/login`, que é capaz de autenticar um usuário baseado no username e password, e caso a autenticação ocorra com sucesso, ele retorna um access token, que deverá ser usado no Header das futuras requisições, nesse formato: `Authorization: Bearer + <access_token>`

## Refresh do Token

De forma similar, podemos usar o Refresh Token para gerar um novo access token. Como o refresh token tem validade de 30 dias, cada vez que o usuário enviar um `POST` para o `/refresh`, validaremos se o refresh token está dentro da validade, e se estiver, ele retorna um novo access token. Futuramente no nosso front, precisaremos consumir essa informação para atualizar o token no local storage.

Então vamos criar essa rota, quase idêntica à rota de login, com a diferença que ao invés de autenticarmos o usuário e senha, vamos validar o refresh token.

Primeiro, criaremos o schema:

```python title="./myapi/code/schemas.py"
class RefreshRequest(Schema):
    refresh_token: str
```

E agora a rota:

```python title="./myapi/core/api.py"
@router.post('refresh', tags=['Auth'], response=TokenResponse)
def refresh(request, credentials: RefreshRequest):
    """Refresh access token using a valid refresh token"""
    user = verify_refresh_token(credentials.refresh_token)
    if not user:
        logger.warning(f'Failed refresh attempt with invalid refresh token')
        raise UnauthorizedError(message='Invalid or expired refresh token')
    logger.info(f'User {user.username} (id={user.id}) refreshed token')
    tokens = create_token(user)
    return 200, {'token_type': 'bearer', **tokens}
```

E no `auth.py` criamos a função `verify_refresh_token()`, também bastante similar ao método `authenticate()`.

```python title="./myapi/core/auth.py"
def verify_refresh_token(token):
    """Verify refresh token and return the user"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGO])
        if payload.get('type') != 'refresh':
            return None
        user_id = payload.get('user_id')
        return User.objects.get(id=user_id)
    except jwt.ExpiredSignatureError:
        return None
    except Exception:
        return None
```

Aí para testar isso, novamente vamos recorrer ao `freezegun`. Vamos simular a criação de um token, avançar 14 minutos, fazer um refresh, validar que recebemos um novo token, avançar mais 10 minutos e ver se ele continua válido. Vamos incluir esse teste no `test_auth.py`:

```python title="./myapi/tests/test_auth.py"
from freezegun import freeze_time

@pytest.mark.django_db
def test_refresh_token_success(client):
    """Test refreshing access token before it expires"""
    # Capture the initial time as reference
    initial_time = timezone.now()

    # Step 1: Login and get tokens
    response = client.post(
        '/api/v1/login',
        data=json.dumps({'username': config('DJANGO_ADMIN_USER'), 'password': config('DJANGO_ADMIN_PASSWORD')}),
        content_type='application/json',
    )
    data = response.json()
    access_token_1 = data['access_token']
    refresh_token = data['refresh_token']
    assert response.status_code == HTTPStatus.OK

    # Step 2: Advance 14 minutes (access token expires in 15)
    with freeze_time(initial_time + timedelta(minutes=14)):
        # Step 3: Call refresh endpoint
        response = client.post(
            '/api/v1/refresh',
            data=json.dumps({'refresh_token': refresh_token}),
            content_type='application/json',
        )
        data = response.json()
        access_token_2 = data['access_token']

        # Step 4: Verify we got a new token (different from the first)
        assert response.status_code == HTTPStatus.OK
        assert 'access_token' in data
        assert access_token_1 != access_token_2  # Token deve ser diferente
        assert data['token_type'] == 'bearer'

        # Step 5: Advance more 10 minutes (total 24 minutes from start)
        # Old access_token_1 should be expired, but access_token_2 should be valid
        with freeze_time(initial_time + timedelta(minutes=24)):
            # Try to use access_token_2 (should still work)
            response = client.get(
                '/api/v1/users',
                HTTP_AUTHORIZATION=f'Bearer {access_token_2}',
            )
            # Should work because token_2 is fresh and only 10 minutes old
            assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_refresh_token_expired(client):
    """Test that expired refresh tokens are rejected"""
    # Login to get tokens
    response = client.post(
        '/api/v1/login',
        data=json.dumps({'username': config('DJANGO_ADMIN_USER'), 'password': config('DJANGO_ADMIN_PASSWORD')}),
        content_type='application/json',
    )
    data = response.json()
    refresh_token = data['refresh_token']

    # Advance 31 days (refresh token expires in 30)
    with freeze_time(timezone.now() + timedelta(days=31)):
        response = client.post(
            '/api/v1/refresh',
            data=json.dumps({'refresh_token': refresh_token}),
            content_type='application/json',
        )

        # Should fail because refresh token is expired
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert 'Invalid or expired refresh token' in response.json()['message']
```

## Protegendo as rotas

Por enquanto temos o sistema de geração de Tokens funcional, mas as rotas ainda não sabem que precisam receber o token no header, e para isso também usaremos a biblioteca do `jwt`.

No Djando, para proteger uma rota é só colocar um `auth=JWTAuth()` no decorator. Por exemplo, para proteger a rota de GET em `/users`:

```python title="./myapi/users/api.py" hl_lines="1 8"
from ..core.auth import JWTAuth

@router.get(
    'users',
    response=list[UserWithGroupsSchema],
    summary='List users',
    description='List users',
    auth=JWTAuth() # <= Adicione isso
)
@paginate
def list_users(request):
    ...
```

Ao fazer isso, o Django Ninja faz assim:

1. Extrai o token do header `Authorization: Bearer {token}`
2. Chama o método `authenticate(request, token)` da classe `JWTAuth`
3. O método decodifica o JWT usando `jwt.decode()`, que **automaticamente valida**:
   - Se o token está válido (assinatura correta)
   - Se o token não está expirado
4. Retorna o usuário autenticado (ou None se qualquer validação falhar)

Aqui está a classe `JWTAuth` implementada no `auth.py`:

```python title="./myapi/core/auth.py"
class JWTAuth(HttpBearer):
    @staticmethod
    def authenticate(self, request, token):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGO])
            if payload.get('type') != 'access':
                return None
            user_id = payload.get('user_id')
            return User.objects.get(id=user_id)
        except jwt.ExpiredSignatureError:
            return None
        except Exception:
            return None
```

!!! success

    Dessa forma, apenas adicionando o `auth=JWTAuth()` já estaremos restringindo o endpoint apenas para usuários logados (com um token válido). Ainda não estamos validando se o usuário tem permissão para executar a ação, e isso é o que iremos implementar já já.

## Testando o endpoint de Login

Agora vamos criar os testes para o endpoint de login. Vamos cobrir os seguintes casos:

1. Login com sucesso do usuário admin (que já está ativo)
2. Login com sucesso de um novo usário após ser ativado
3. Login sem sucesso de um usuário inativo
4. Login sem sucesso de um usuário com credenciais inválidas
5. Login sem sucesso de um request faltando dados de usuário e senha

```python title="./myapi/core/tests/test_auth.py"
import json
from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from decouple import config


User = get_user_model()

@pytest.mark.django_db
def test_login_success(client):
    response = client.post(
        '/api/v1/login',
        data=json.dumps({'username': config('DJANGO_ADMIN_USER'), 'password': config('DJANGO_ADMIN_PASSWORD')}),
        content_type='application/json',
    )
    data = response.json()
    assert response.status_code == HTTPStatus.OK
    assert 'access_token' in data
    assert data['token_type'] == 'bearer'
    assert 'refresh_token' in data


@pytest.mark.django_db
def test_login_inactive_user(client):
    """Test that inactive users cannot login"""
    # Create a new user (created as inactive by default)
    user_payload = {
        'username': 'inactive_user',
        'first_name': 'Inactive',
        'last_name': 'User',
        'email': 'inactive@test.com',
        'password': 'testpassword',
    }
    response = client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )
    assert response.status_code == HTTPStatus.CREATED

    # Try to login with inactive user
    response = client.post(
        '/api/v1/login',
        data=json.dumps({'username': 'inactive_user', 'password': 'testpassword'}),
        content_type='application/json',
    )

    # Should return 403 Forbidden
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_login_invalid_credentials(client):
    response = client.post(
        '/api/v1/login',
        data=json.dumps({'username': config('DJANGO_ADMIN_USER'), 'password': 'wrongpassword'}),
        content_type='application/json',
    )
    data = response.json()
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert data['detail'] == 'Invalid credentials'

@pytest.mark.django_db
def test_login_missing_fields(client):
    response = client.post(
        '/api/v1/login',
        data=json.dumps({}),
        content_type='application/json',
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY or response.status_code == 422
```

Certo, mas esse teste é basicamente para ver se estamos conseguindo gerar o Token. Mas veja que ao proteger as rotas de CRUD de Users, quebramos os testes, porque agora precisamos passar uma autenticação. Vamos corrigir isso criando uma fixture de geração de Token antes de rodar os testes que já tinhamos criado.

```python title="./myapi/users/tests/test_users.py"
@pytest.fixture
def create_admin_access_token(client):
    response = client.post(
        '/api/v1/login',
        data=json.dumps({'username': config('DJANGO_ADMIN_USER'), 'password': config('DJANGO_ADMIN_PASSWORD')}),
        content_type='application/json',
    )
    response_json = response.json()
    access_token = response_json['access_token']
    return access_token
```

E agora basta chamar essa fixture nos testes que precisam de autenticação, e enviar o header com o Token. Mas veja que o TestClient do Django não aceita passarmos um header={} como no requests, precisamos especificar os cabeçalhos como argumentos nomeados com o prefixo `HTTP_`, por exemplo `HTTP_AUTHORIZATION`:

```python title="./myapi/users/tests/test_users.py"
@pytest.mark.django_db
def test_list_users(client, create_admin_access_token):
    response = client.get('/api/v1/users', HTTP_AUTHORIZATION=f'Bearer {create_admin_access_token}')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['count'] == 1
    assert data['items'][0]['username'] == 'admin'
```

!!! warning

    Todos os testes devem ser corrigidos para receber a fixture `create_admin_access_token`, e passar o token no header da requisição.

!!! success

    Agora temos a autenticação funcionando, assim com todos os testes que dependem dela! 🙌🙌🙌

## Autorização

Por enquanto, estamos apenas validando se o usuário está autenticado para poder executar essas operações, mas na verdade a gente precisa que apenas Usuários **ADMIN** possam fazer certas operações, como listar, deletar e alterar usuários. Não queremos que um usuário qualquer logado posso fazer isso, né? Aí que entra a autorização.

Faremos o seguinte: o usuário admin pode fazer tudo isso, mas o usuário não admin (porém ativo) poderá listar os detalhes dele mesmo, alterar as configurações dele mesmo, e apagar ele mesmo.

Vamos começar com as rotas que são permitidas apenas pelos admins. Uma forma fácil seria verificar dentro da própria rota com a propriedade `is_staff`, assim:

```python title="./myapi/users/api.py"
@router.get('users', response=list[UserWithGroupsSchema], auth=JWTAuth())
@paginate
def list_users(request):
    user = request.auth
    if not user or not user.is_staff:
        return Response({'detail': 'Forbidden'}, status=403)
    return User.objects.all()
```

Mas se formos usar isso em muitas rotas, compensa criar uma classe que valida se o usuário é Admin, e colocamos ela no decorator de cada rota. Vamos implementar dessa forma. No arquivo `auth.py`, vamos adicionar a classe AdminAuth, herdando do `JWTAuth` que já tinhamos criado antes:

```python title="./myapi/core/auth.py" hl_lines="16-24"
# Classe já existente
class JWTAuth(HttpBearer):
    @staticmethod
    def authenticate(self, request, token):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGO])
            if payload.get('type') != 'access':
                return None
            user_id = payload.get('user_id')
            return User.objects.get(id=user_id)
        except jwt.ExpiredSignatureError:
            return None
        except Exception:
            return None

# Criar essa classe nova
class AdminAuth(JWTAuth):
    def authenticate(self, request, token):
        user = super().authenticate(request, token)
        if not user:
            return None
        if not getattr(user, "is_staff", False):
            return None
        return user
```

E agora no `api.py` vamos importar essa classe e chamá-la no decorator das rotas que precisam de permissão de Admin:

```python title="./myapi/users/api.py" hl_lines="8"
from ..core.auth import JWTAuth, AdminAuth

@router.get(
    'users',
    response=list[UserWithGroupsSchema],
    summary='List users',
    description='List users or filter by id/username',
    auth=AdminAuth(),
)
@paginate
def list_users(request, id: uuid.UUID = None, username: str = None):
    ...
```

Agora quando um usuário normal (não admin) tentar chamar essa rota, ele vai tomar um erro 401. Mas vamos criar testes para isso. As rotas de `GET` de detalhes de usuário, de `PATCH` e `DELETE` vamos fazer diferente, porque um usuário não admin poderia também chamá-las caso o usuário destino for eles mesmos.

Para testar, criaremos uma nova Fixture que cria um usuário não admin, ativa ele, e o autentica. Usaremos esse access token nas rotas que precisam de admin, para confirmar se a API retorna 401:

```python title="./myapi/users/tests/test_users.py"
@pytest.fixture
def create_non_admin_access_token(client):
    # Create new non-admin user
    user_payload = {
        'username': 'new_user_non_admin',
        'first_name': 'New',
        'last_name': 'User',
        'email': 'user_new@admin.com',
        'password': 'myuserpassword',
    }
    response = client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )

    # Activate the user (he was created as inactive)
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')
    user.is_active = True
    user.save()

    # Get the auth token for the non-admin user
    response = client.post(
        '/api/v1/login',
        data=json.dumps({'username': 'new_user_non_admin', 'password': 'myuserpassword'}),
        content_type='application/json',
    )
    response_json = response.json()
    access_token = response_json['access_token']
    return access_token

@pytest.mark.django_db
def test_list_users_unauthorized(client, create_non_admin_access_token):
    response = client.get('/api/v1/users', HTTP_AUTHORIZATION=f'Bearer {create_non_admin_access_token}')

    assert response.status_code == HTTPStatus.UNAUTHORIZED
```

Ótimo, agora para as rotas de `UPDATE`, `DELETE` e `GET` de detalhes de usuários, vamos validar se o usuário logado é admin ou se é ele mesmo. Para todas essas rotas a gente passa o id do usuário alvo na URL do request, então precisamos comparar se o id é o mesmo do id do usuário logado. Também tem várias formas de implementar isso, mas para manter consistência, vamos fazer da mesma forma, criando uma classe `OwnerOrAdminAuth`, herdando de `JWTAuth`, e chamando no decorator das rotas.

```python title="./myapi/core/auth.py"
class OwnerOrAdminAuth(JWTAuth):
    def authenticate(self, request, token):
        user = super().authenticate(request, token)
        if not user:
            return None

        # resolver_match.kwargs contém os parâmetros nomeados da URL já resolvidos pelo Django
        target_identifier = str(request.resolver_match.kwargs.get('id', ''))

        # Se não há target_identifier, só admins tem acesso
        if not target_identifier:
            return user if getattr(user, 'is_staff', False) else None

        # Verifica se é admin
        if getattr(user, 'is_staff', False):
            return user

        # Para não-admins, verifica se é o próprio usuário
        if str(user.id) == target_identifier:
            return user

        return None
```

Agora na API é só importar a classe e chamar nos decorators:

```python title="./myapi/users/api.py" hl_lines="8"
from ..core.auth import JWTAuth, AdminAuth, OwnerOrAdminAuth

@router.get(
    'users/{id}',
    response=UserWithGroupsSchema,
    summary='Get user detail',
    description='Retrieve user details by ID',
    auth=OwnerOrAdminAuth(), #<= Alterar aqui
)
def get_user_detail(request, id: uuid.UUID):
    ...
```

Vamos aplicar a mesma coisa nas rotas de `PATCH` e `DELETE`, e fazer os testes.

```python title="./myapi/users/tests/test_users.py"
# Teste do admin fazendo o GET nele mesmo
@pytest.mark.django_db
def test_get_user_detail_admin(client, create_admin_access_token):
    User = get_user_model()
    admin = User.objects.get(username=config('DJANGO_ADMIN_USER'))

    response = client.get(f'/api/v1/users/{admin.id}', HTTP_AUTHORIZATION=f'Bearer {create_admin_access_token}')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['username'] == config('DJANGO_ADMIN_USER')

# Teste do admin fazendo o GET em outro usuário
@pytest.mark.django_db
def test_get_user_detail_admin_to_other_user(client, create_admin_access_token, create_non_admin_access_token):
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    response = client.get(f'/api/v1/users/{user.id}', HTTP_AUTHORIZATION=f'Bearer {create_admin_access_token}')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['username'] == 'new_user_non_admin'


# Teste de um usuário não admin fazendo GET nele mesmo
@pytest.mark.django_db
def test_get_user_detail_user_to_himself(client, create_non_admin_access_token):
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    response = client.get(f'/api/v1/users/{user.id}', HTTP_AUTHORIZATION=f'Bearer {create_non_admin_access_token}')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['username'] == 'new_user_non_admin'

# Teste de um usuário fazendo GET em outro usuário (Falha!)
@pytest.mark.django_db
def test_get_user_detail_user_to_other_user_fail(client, create_non_admin_access_token):
    User = get_user_model()
    user_admin = User.objects.get(username=config('DJANGO_ADMIN_USER'))

    response = client.get(f'/api/v1/users/{user_admin.id}', HTTP_AUTHORIZATION=f'Bearer {create_non_admin_access_token}')
    assert response.status_code == HTTPStatus.UNAUTHORIZED

# Teste de delete de um usuário pelo admin
@pytest.mark.django_db
def test_delete_user_admin_to_other_user(client, create_admin_access_token, create_non_admin_access_token):
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    response = client.delete(f'/api/v1/users/{user.id}', HTTP_AUTHORIZATION=f'Bearer {create_admin_access_token}')
    assert response.status_code == HTTPStatus.NO_CONTENT

# Teste de delete de um usuário por ele mesmo
@pytest.mark.django_db
def test_delete_user_to_himself(client, create_non_admin_access_token):
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    response = client.delete(f'/api/v1/users/{user.id}', HTTP_AUTHORIZATION=f'Bearer {create_non_admin_access_token}')
    assert response.status_code == HTTPStatus.NO_CONTENT

# Teste de delete de um usuário por outro usuário (Falha!)
@pytest.mark.django_db
def test_delete_user_to_other_user_fail(client, create_non_admin_access_token):
    User = get_user_model()
    user_admin = User.objects.get(username=config('DJANGO_ADMIN_USER'))

    response = client.delete(f'/api/v1/users/{user_admin.id}', HTTP_AUTHORIZATION=f'Bearer {create_non_admin_access_token}')
    assert response.status_code == HTTPStatus.UNAUTHORIZED

# Teste de patch de um usuário pelo admin
@pytest.mark.django_db
def test_patch_user_admin_to_other_user(client, create_admin_access_token, create_non_admin_access_token):
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    patch_data = {
        'first_name': 'NewName',
        'email': 'newemail@admin.com',
    }

    response = client.patch(
        f'/api/v1/users/{user.id}',
        data=json.dumps(patch_data),
        HTTP_AUTHORIZATION=f'Bearer {create_admin_access_token}',
    )
    response_json = response.json()
    assert response.status_code == HTTPStatus.OK
    assert response_json['first_name'] == 'NewName'
    assert response_json['email'] == 'newemail@admin.com'

# Teste de patch de um usuário por ele mesmo
@pytest.mark.django_db
def test_patch_user_to_himself(client, create_non_admin_access_token):
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    patch_data = {
        'first_name': 'NewName',
        'email': 'newemail@admin.com',
    }

    response = client.patch(
        f'/api/v1/users/{user.id}',
        data=json.dumps(patch_data),
        HTTP_AUTHORIZATION=f'Bearer {create_non_admin_access_token}',
    )
    response_json = response.json()
    assert response.status_code == HTTPStatus.OK
    assert response_json['first_name'] == 'NewName'
    assert response_json['email'] == 'newemail@admin.com'

# Teste de patch de um usuário por outro usuário (Falha!)
@pytest.mark.django_db
def test_patch_user_to_other_user_fail(client, create_non_admin_access_token):
    User = get_user_model()
    user_admin = User.objects.get(username=config('DJANGO_ADMIN_USER'))

    patch_data = {
        'first_name': 'NewName',
        'email': 'newemail@admin.com',
    }

    response = client.patch(
        f'/api/v1/users/{user_admin.id}',
        data=json.dumps(patch_data),
        HTTP_AUTHORIZATION=f'Bearer {create_non_admin_access_token}',
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED
```

## Criando o endpoint `/me`

O endpoint `/me` será usado para pegar os detalhes do próprio usuário que está logado, e isso com JWT é muito fácil, porque o Token já tem esse dado encodado na string. Se chamarmos o `JWTAuth()`, ele já faz a autenticação e retorna o usuário em `request.auth`. Com isso, já temos acesso ao usuário logado:

```python title="./myapi/users/api.py"
##############
# Me (Current User)
##############
@router.get(
    'me',
    response=UserWithGroupsSchema,
    summary='Get current user',
    description='Get the current authenticated user information',
    auth=JWTAuth(),
)
def get_current_user(request):
    logger.info(f'User {request.auth.username} retrieved their profile')
    return request.auth
```

Vamos adicionar esses testes:

```python title="./muapi/users/test_users.py"
##############
# Me (Current User)
##############
@pytest.mark.django_db
def test_get_current_user_admin(client, create_admin_access_token):
    """Test that admin can get their own profile"""
    response = client.get(
        '/api/v1/me',
        HTTP_AUTHORIZATION=f'Bearer {create_admin_access_token}',
    )
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['username'] == config('DJANGO_ADMIN_USER')
    assert 'email' in data
    assert 'id' in data


@pytest.mark.django_db
def test_get_current_user_non_admin(client, create_non_admin_access_token):
    """Test that non-admin user can get their own profile"""
    response = client.get(
        '/api/v1/me',
        HTTP_AUTHORIZATION=f'Bearer {create_non_admin_access_token}',
    )
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['username'] == 'new_user_non_admin'
    assert data['email'] == 'user_new@admin.com'
    assert 'id' in data
```

!!! success

    Com isso a gente termina a Autenticação e Autorização do CRUD de Users

---

## Rotação de Refresh Token

### O problema

No fluxo atual, o refresh token é um JWT **stateless**: não há registro no banco de que ele foi emitido, e o mesmo token pode ser usado quantas vezes quiser durante os 30 dias de validade. Se um atacante roubar o refresh token do cookie de um usuário, ele consegue manter acesso indefinidamente — sem que o usuário ou o servidor consiga perceber.

### A solução: rotação com `jti` + denylist

A rotação funciona assim:

1. Cada refresh token gerado recebe um **`jti`** (JWT ID) — um UUID único no payload
2. Ao usar o token em `POST /refresh`, o `jti` é registrado em uma tabela de denylist no banco
3. Se o mesmo token for apresentado novamente, o `jti` já estará na denylist → request rejeitado
4. A cada chamada ao `/refresh`, entradas já expiradas são deletadas da denylist (limpeza oportunista)

Com isso, cada refresh token só pode ser usado **uma única vez**. Um token roubado e já utilizado pelo atacante seria detectado quando o usuário legítimo tentar um novo refresh — a sessão seria encerrada.

### Criando o modelo `RefreshTokenDenylist`

No arquivo `./myapi/core/models.py`, vamos criar o modelo que guardará os `jti` dos tokens já utilizados:

```python title="./myapi/core/models.py"
import uuid
from datetime import datetime, timezone

from django.db import models


class RefreshTokenDenylist(models.Model):
    jti = models.UUIDField(unique=True, db_index=True)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [models.Index(fields=['expires_at'])]

    @classmethod
    def cleanup_expired(cls):
        cls.objects.filter(expires_at__lt=datetime.now(tz=timezone.utc)).delete()
```

O índice em `expires_at` torna o `DELETE` de entradas expiradas eficiente mesmo com a tabela crescendo.

Depois de criar o modelo, rode:

```bash
python manage.py makemigrations core
python manage.py migrate
```

### Alterando o `auth.py`

Duas mudanças em `./myapi/core/auth.py`:

**`create_token`** — adiciona o `jti` no payload do refresh token:

```python title="./myapi/core/auth.py" hl_lines="1 12-13"
from uuid import uuid4

def create_token(user):
    now = datetime.utcnow()
    access_token = jwt.encode(
        {'user_id': str(user.id), 'exp': now + ACCESS_LIFETIME, 'type': 'access'},
        settings.SECRET_KEY,
        algorithm=ALGO,
    )
    refresh_token = jwt.encode(
        {
            'user_id': str(user.id),
            'exp': now + REFRESH_LIFETIME,
            'type': 'refresh',
            'jti': str(uuid4()),   # <= UUID único por token
        },
        settings.SECRET_KEY,
        algorithm=ALGO,
    )
    return {'access_token': access_token, 'refresh_token': refresh_token}
```

**`verify_refresh_token`** — verifica a denylist, registra o `jti` usado e limpa entradas expiradas:

```python title="./myapi/core/auth.py"
from datetime import datetime, timezone

from .models import RefreshTokenDenylist

def verify_refresh_token(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGO])
        if payload.get('type') != 'refresh':
            return None

        jti = payload.get('jti')
        exp = payload.get('exp')

        # Limpeza oportunista: remove entradas expiradas do banco a cada chamada
        RefreshTokenDenylist.cleanup_expired()

        # Rejeita se o jti já foi usado (token reutilizado ou roubado)
        if RefreshTokenDenylist.objects.filter(jti=jti).exists():
            return None

        # Registra o jti como utilizado
        RefreshTokenDenylist.objects.create(
            jti=jti,
            expires_at=datetime.fromtimestamp(exp, tz=timezone.utc),
        )

        user_id = payload.get('user_id')
        return User.objects.get(id=user_id)

    except jwt.ExpiredSignatureError:
        return None
    except Exception:
        return None
```

!!! note

    O endpoint `POST /refresh` em `./myapi/core/api.py` **não precisa de nenhuma alteração** — ele já chama `verify_refresh_token` → `create_token`. A lógica de rotação fica inteiramente nas funções do `auth.py`.

### Testes

Vamos adicionar dois novos testes em `./myapi/core/tests/test_auth.py`:

```python title="./myapi/core/tests/test_auth.py"
@pytest.mark.django_db
def test_refresh_token_rotation(client):
    """Um refresh token só pode ser usado uma vez."""
    client.post(
        '/api/v1/login',
        data=json.dumps({'username': config('DJANGO_ADMIN_USER'), 'password': config('DJANGO_ADMIN_PASSWORD')}),
        content_type='application/json',
    )

    # Primeiro refresh: deve funcionar
    response = client.post('/api/v1/refresh')
    assert response.status_code == HTTPStatus.OK

    # Segundo refresh com o mesmo cookie (token já usado): deve falhar
    response = client.post('/api/v1/refresh')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_refresh_token_cleanup(client):
    """Entradas expiradas são removidas da denylist a cada chamada ao /refresh."""
    from myapi.core.models import RefreshTokenDenylist
    from datetime import datetime, timezone, timedelta
    import uuid

    # Cria uma entrada já expirada na denylist manualmente
    RefreshTokenDenylist.objects.create(
        jti=uuid.uuid4(),
        expires_at=datetime.now(tz=timezone.utc) - timedelta(days=1),
    )
    assert RefreshTokenDenylist.objects.count() == 1

    # Faz login e usa o /refresh — deve limpar a entrada expirada
    client.post(
        '/api/v1/login',
        data=json.dumps({'username': config('DJANGO_ADMIN_USER'), 'password': config('DJANGO_ADMIN_PASSWORD')}),
        content_type='application/json',
    )
    client.post('/api/v1/refresh')

    # A entrada expirada deve ter sido removida; apenas o jti do refresh atual existe
    assert RefreshTokenDenylist.objects.count() == 1
```

!!! success

    Com a rotação ativa, cada refresh token é válido para **um único uso**. Um token roubado que já foi utilizado pelo atacante será detectado na próxima tentativa legítima, encerrando a sessão comprometida.
