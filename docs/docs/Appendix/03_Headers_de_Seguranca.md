# Headers de Segurança

Headers HTTP de segurança instruem o browser sobre como se comportar ao lidar com a aplicação — bloqueando clickjacking, forçando HTTPS, impedindo sniffing de MIME type, entre outros. São uma camada de defesa de baixo custo e alto impacto.

## Headers configurados via `settings.py`

O Django já inclui o `SecurityMiddleware` (primeiro da lista em `MIDDLEWARE`), que aplica automaticamente vários headers a partir das settings abaixo.

### HSTS — HTTP Strict Transport Security

HSTS instrui o browser a **sempre usar HTTPS** para este domínio, mesmo que o usuário tente acessar via `http://`. Após o primeiro acesso, o browser recusa conexões HTTP sem nem consultar o servidor.

Adicionamos essas settings dentro do bloco `IS_PRODUCTION` no `settings.py`, pois HSTS em localhost quebraria o ambiente de desenvolvimento:

```python title="./myapi/settings.py" hl_lines="9-11"
if IS_PRODUCTION:
    USE_X_FORWARDED_HOST = True
    USE_X_FORWARDED_PROTO = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000       # 1 ano
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True  # cobre myapi. e react.
    SECURE_HSTS_PRELOAD = True           # permite entrar na lista de preload dos browsers
```

!!! warning

    `SECURE_HSTS_PRELOAD = True` só deve ser ativado quando você tiver certeza que **todo** o domínio (incluindo subdomínios) estará permanentemente em HTTPS. Uma vez na lista de preload dos browsers, remover é um processo lento.

### Headers globais (dev + prod)

```python title="./myapi/settings.py"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'
```

| Setting | Header gerado | O que faz |
|---------|--------------|-----------|
| `SECURE_CONTENT_TYPE_NOSNIFF` | `X-Content-Type-Options: nosniff` | Impede que o browser "adivinhe" o MIME type de uma resposta, evitando ataques de MIME sniffing |
| `SECURE_REFERRER_POLICY` | `Referrer-Policy: strict-origin-when-cross-origin` | Envia a URL de origem apenas para requests same-origin; para cross-origin, envia só o domínio (sem path) |
| `X_FRAME_OPTIONS` | `X-Frame-Options: DENY` | Impede que a aplicação seja embutida em `<iframe>`, evitando ataques de clickjacking |

---

## Headers via `SecurityHeadersMiddleware`

Alguns headers não são cobertos pelo `SecurityMiddleware` nativo do Django. Para adicioná-los, criamos um middleware simples em `./myapi/core/middleware.py`:

```python title="./myapi/core/middleware.py"
class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response['Cross-Origin-Opener-Policy'] = 'same-origin'
        return response
```

E registramos no final da lista de `MIDDLEWARE` no `settings.py`:

```python title="./myapi/settings.py" hl_lines="5"
MIDDLEWARE = [
    ...
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'myapi.core.middleware.SecurityHeadersMiddleware',
]
```

| Header | Valor | O que faz |
|--------|-------|-----------|
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` | Desativa explicitamente o acesso a câmera, microfone e geolocalização — recursos que esta API não usa |
| `Cross-Origin-Opener-Policy` | `same-origin` | Isola o contexto de navegação de janelas abertas cross-origin, protegendo contra ataques de side-channel como Spectre |

!!! success

    Com esses headers configurados, a aplicação passa nas auditorias de segurança mais comuns (ex: [securityheaders.com](https://securityheaders.com)) e segue as recomendações do OWASP para hardening de HTTP headers.
