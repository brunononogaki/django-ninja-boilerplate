# CLAUDE.md

> Copie este arquivo para `CLAUDE.md` e preencha as seções marcadas com `TODO` antes de começar a codar.
> O restante já descreve a arquitetura do boilerplate e não precisa ser alterado (apenas atualizado conforme o projeto evolui).

---

## Visão geral do projeto

**TODO — descreva o produto em 3-5 frases:**
- O que o sistema faz
- Quem são os usuários
- Qual problema resolve

---

## Escopo e regras de negócio

**TODO — liste as principais regras de negócio:**

### Entidades principais

**TODO — descreva as entidades do domínio:**
- `User` — já existe (ver `users/models.py`)
- `<Entidade>` — TODO

### Regras

**TODO — exemplos do que colocar aqui:**
- Um usuário só pode acessar seus próprios recursos
- Somente staff pode fazer X
- Um pedido não pode ser cancelado após Y

### Fluxos principais

**TODO — descreva os fluxos críticos:**
1. Cadastro e ativação de conta
2. ...

---

## Arquitetura

### Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Django 5.2 + Django Ninja + Python 3.13 |
| Frontend | Next.js (React) |
| Banco de dados | PostgreSQL 17 via psycopg3 |
| Autenticação | JWT em cookies httpOnly (implementação própria) |
| OAuth | Google via django-allauth |
| Reverse proxy | Traefik |
| CDN / proxy externo | Cloudflare |
| Task queue (opcional) | Celery + Redis |
| Package manager (backend) | Poetry |
| Package manager (frontend) | npm |

### Estrutura de pastas

```
.
├── myapp/               # Django project (renomeado pelo setup-my-saas.py)
│   ├── settings.py
│   ├── urls.py
│   ├── core/            # App de infraestrutura: auth, middleware, exceções
│   │   ├── auth.py
│   │   ├── exceptions.py
│   │   ├── middleware.py
│   │   ├── models.py    # RefreshTokenDenylist
│   │   └── tests/
│   └── users/           # App de usuários: CRUD, ativação, reset de senha
│       ├── api.py
│       ├── models.py
│       ├── schemas.py
│       ├── services.py
│       └── tests/
├── next/                # Frontend Next.js
├── infra/               # Dockerfiles, compose, scripts de infra
├── .github/workflows/   # CI/CD
└── docs/                # MkDocs
```

### Padrão de cada app Django

Cada feature segue a separação:

- **`api.py`** — rotas (Django Ninja). Só valida entrada e chama services.
- **`schemas.py`** — schemas Pydantic de entrada e saída.
- **`services.py`** — lógica de negócio. Sem acesso direto ao request.
- **`models.py`** — modelos ORM.

Nunca coloque lógica de negócio em `api.py` nem acesse o ORM direto em `api.py`.

### Autenticação

JWT em cookies httpOnly — implementado em `core/auth.py`:

- `access_token`: 15 minutos
- `refresh_token`: 30 dias (com denylist no banco via `RefreshTokenDenylist`)
- Cookie `is_logged_in`: não-httpOnly, usado pelo frontend para saber o estado sem ler o JWT

Três classes de autenticação prontas para usar nos endpoints:

```python
from myapp.core.auth import JWTAuth, AdminAuth, OwnerOrAdminAuth

@router.get("/recurso", auth=JWTAuth())          # qualquer usuário autenticado
@router.get("/admin", auth=AdminAuth())           # só staff
@router.get("/recurso/{id}", auth=OwnerOrAdminAuth())  # dono do recurso ou staff
```

### Exceções

Sempre levante as exceções de `core/exceptions.py`. O handler global as converte para JSON padronizado:

```python
from myapp.core.exceptions import NotFoundError, ConflictError, ValidationError, UnauthorizedError, ServiceError

raise NotFoundError("Pedido não encontrado.")
raise ConflictError("E-mail já cadastrado.")
```

Nunca retorne erros como dicionários ou strings soltas nos endpoints.

### Segurança

- `SecurityHeadersMiddleware` adiciona `Permissions-Policy` e `Cross-Origin-Opener-Policy` em todas as respostas.
- Rate limiting via `django-ratelimit` (configurado por endpoint).
- Cloudflare filtra todo o tráfego externo antes de chegar ao servidor.
- Apenas IPs da Cloudflare chegam às portas 80/443 (regra `DOCKER-USER` no iptables do servidor).
- SSH só aceita chave pública (`PermitRootLogin prohibit-password`).

---

## CI/CD e qualidade

### Pipelines (GitHub Actions)

Todos rodam em **pull request**:

| Workflow | O que faz |
|----------|-----------|
| `lint.yaml` | Ruff + Commitizen (valida mensagens de commit) |
| `tests.yaml` | pytest com banco real (PostgreSQL via Docker) |
| `trivy.yaml` | Scan de vulnerabilidades em dependências e na imagem Docker |
| `semgrep.yaml` | Análise estática de segurança no código |

Deploy roda no **push para `main`**: rsync para o VPS → `deploy.sh` (docker compose up + migrate).

### Regras inegociáveis

- **Todo código novo precisa de teste.** Sem exceção. Testes ficam em `<app>/tests/`.
- **Testes batem no banco real.** Não use mocks de ORM — o projeto já configura PostgreSQL no CI.
- **Commits seguem Conventional Commits.** Use `poetry run task commit` para guiar o formato. O CI rejeita commits fora do padrão.
- **Sem `# noqa` sem justificativa.** Se precisar suprimir uma regra do Ruff, explique por quê no comentário.
- **Trivy e Semgrep são bloqueantes.** PRs com vulnerabilidades `HIGH` ou `CRITICAL` não são mergeados.

### Comandos úteis

```bash
poetry run task run          # sobe tudo e roda o servidor de dev
poetry run task test         # roda os testes
poetry run task format       # formata o código (ruff format + ruff check --fix)
poetry run task migrate      # makemigrations + migrate
poetry run task commit       # assistente de commit (commitizen)
```

---

## Variáveis de ambiente

Copie `.env.production.example` → `.env.production` e preencha:

| Variável | Descrição |
|----------|-----------|
| `SECRET_KEY` | Chave secreta do Django |
| `BACKEND_FQDN` | Domínio do backend (ex: `api.meuapp.com`) |
| `FRONTEND_FQDN` | Domínio do frontend (ex: `app.meuapp.com`) |
| `COOKIE_DOMAIN` | Domínio raiz para cookies (ex: `.meuapp.com`) |
| `POSTGRES_*` | Credenciais do banco |
| `GMAIL_EMAIL` / `GMAIL_APP_PASSWORD` | Para envio de e-mails |

---

## O que ainda não está implementado neste projeto

**TODO — liste aqui o que falta construir, à medida que for descobrindo:**

- [ ] ...
