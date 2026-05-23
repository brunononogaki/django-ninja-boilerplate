# Rate Limiting

## Por que Rate Limiting?

Sem rate limiting, qualquer um pode fazer chamadas ilimitadas aos nossos endpoints. Os endpoints mais críticos são os de autenticação, pois um atacante poderia:

- **Login**: tentar senhas diferentes até achar a correta (brute force)
- **Cadastro / reset de senha**: enviar milhares de e-mails através da nossa conta (spam abuse)
- **Reenvio de ativação**: sobrecarregar o servidor de e-mail

## Estratégia adotada

Utilizaremos duas camadas de proteção:

| Camada | Ferramenta | Objetivo |
|--------|-----------|----------|
| Infraestrutura | Traefik | Rate limit global por IP — proteção contra flood e DDoS |
| Aplicação | `django-ratelimit` | Rate limit específico por endpoint para os endpoints críticos |

O Traefik barra requisições antes de chegarem no Django, mas não consegue distinguir `/login` de `/status`. O `django-ratelimit` completa isso aplicando limites mais rígidos somente onde é necessário.

---

## Parte 1: Rate Limit Global no Traefik

No arquivo `./infra/compose-pro.yaml`, vamos adicionar um middleware de rate limit e aplicá-lo ao router do backend:

```yaml title="./infra/compose-pro.yaml" hl_lines="8-11 14"
  web:
    ...
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.myapi.rule=Host(`${BACKEND_FQDN}`)"
      - "traefik.http.routers.myapi.entrypoints=websecure"
      - "traefik.http.routers.myapi.tls=true"
      - "traefik.http.routers.myapi.tls.certresolver=letsencrypt"
      - "traefik.http.routers.myapi.middlewares=myapi-ratelimit"
      - "traefik.http.middlewares.myapi-ratelimit.rateLimit.average=100"
      - "traefik.http.middlewares.myapi-ratelimit.rateLimit.burst=50"
      - "traefik.http.middlewares.myapi-ratelimit.rateLimit.period=1m"
      - "traefik.http.services.myapi.loadbalancer.server.port=8000"
      - "traefik.docker.network=my-network"
```

**O que esse limite significa:**

- `average=100` + `period=1m`: permite até 100 requisições por minuto por IP
- `burst=50`: permite um pico momentâneo de até 50 requisições extras (acima da média) antes de começar a bloquear

!!! note

    Ajuste os valores conforme o perfil esperado da sua aplicação. Para uma API pública com muitos usuários simultâneos, valores maiores podem ser necessários.

---

## Parte 2: Rate Limit por Endpoint com `django-ratelimit`

### Instalação

```bash
poetry add django-ratelimit
```

Não é necessário adicionar ao `INSTALLED_APPS` para o uso funcional que faremos.

### Como funciona

O `django-ratelimit` usa o **cache do Django** para armazenar os contadores por IP. Por padrão, o Django usa cache em memória (`LocMemCache`), que funciona bem para desenvolvimento e para ambientes com um único processo.

!!! warning "Produção com múltiplos workers"

    Se você roda a aplicação com múltiplos workers (ex: `uvicorn --workers 4`), o cache em memória é isolado por processo — cada worker teria seu próprio contador. Para que o rate limit funcione corretamente nesse caso, configure o Redis como backend de cache no `settings.py`:

    ```python
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": config("REDIS_URL", default="redis://localhost:6379"),
        }
    }
    ```

### Criando um helper reutilizável

Para não repetir a lógica em cada endpoint, vamos criar uma função auxiliar em `myapi/core/ratelimit.py`:

```python title="myapi/core/ratelimit.py"
from django_ratelimit.core import is_ratelimited
from ninja.errors import HttpError


def check_rate_limit(request, group: str, rate: str = '5/m') -> None:
    limited = is_ratelimited(request, group=group, key='ip', rate=rate, increment=True)
    if limited:
        raise HttpError(429, 'Muitas tentativas. Tente novamente mais tarde.')
```

### Aplicando nos endpoints críticos

Vamos aplicar o rate limit nos seguintes endpoints em `myapi/core/api.py` e `myapi/users/api.py`:

| Endpoint | Rate | Justificativa |
|----------|------|---------------|
| `POST /auth/login` | `5/m` | Brute force de senha |
| `POST /users` (cadastro) | `5/m` | Abuso de criação de contas |
| `POST /users/{id}/request-password-reset` | `3/m` | Abuso de envio de e-mail |
| `POST /users/{id}/resend-activation` | `3/m` | Abuso de envio de e-mail |

**`myapi/core/api.py` — endpoint de login:**

```python title="myapi/core/api.py" hl_lines="3 7"
from myapi.core.ratelimit import check_rate_limit

@router.post('/auth/login', auth=None, tags=['Auth'])
def login(request, response: HttpResponse, credentials: LoginRequest):
    check_rate_limit(request, group='login')
    ...
```

**`myapi/users/api.py` — endpoints de usuários:**

```python title="myapi/users/api.py" hl_lines="3 8 13 18"
from myapi.core.ratelimit import check_rate_limit

@router.post('/users', auth=None, tags=['Users'])
def create_users(request, data: UserCreateSchema):
    check_rate_limit(request, group='register')
    ...

@router.post('/users/{token_id}/request-password-reset', auth=None, tags=['Users'])
def request_password_reset(request, data: PasswordResetRequestSchema):
    check_rate_limit(request, group='password-reset', rate='3/m')
    ...

@router.post('/users/{token_id}/resend-activation', auth=None, tags=['Users'])
def resend_activation(request, token_id: uuid.UUID):
    check_rate_limit(request, group='resend-activation', rate='3/m')
    ...
```

### Resposta retornada ao cliente

Quando o limite é atingido, a API retorna:

```json
HTTP 429 Too Many Requests

{ "detail": "Muitas tentativas. Tente novamente mais tarde." }
```

---

## Testando

Para testar manualmente que o rate limit está funcionando, você pode usar o `curl` em loop:

```bash
for i in {1..10}; do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username": "test@test.com", "password": "wrongpassword"}'
done
```

As primeiras 5 requisições retornarão `401` (credenciais inválidas) e as seguintes retornarão `429` (rate limit atingido).

!!! success

    Com as duas camadas configuradas, o projeto está protegido contra ataques de força bruta e abuso dos endpoints de autenticação.
