# Implementando o sistema de ativação de contas

Até esse momento, temos a rota para criar o usuário, mas por uma questão de design, optei por deixar o endpoint de criação (POST) aberto, pois o usuário anônimo poderá fazer o seu cadastro. Dependendo do sistema, você pode deixar isso como sendo apenas uma tarefa de um `admin`, por exemplo. No nosso boilerplate, o fluxo será através do recebimento de um e-mail. Ao criar o cadastro, o usuário vai receber um e-mail com um link para fazer a ativação, e somente depois disso que ele estará ativo e capaz de interagir com a plataforma.

Para montar esse link, precisamos gerar dinamicamente tokens de ativação que terão um tempo de validade de, por exemplo, 15 minutos. Esses tokens precisam ser armazenados em uma tabela no banco de dados, para termos controle dos tokens que foram gerados, a data de expiração, marcar se ele já foi usado ou não, etc. Vamos implementar tudo isso passo a passo.

## Criando a tabela `ActivationToken`

Vamos primeiramente criar uma nova tabela no Banco para armazenar esse dado. Essa tabela é criada via Migrations a partir de um model. Podemos criar esse model dentro do app `users`, junto com o model UUIDUser que criamos antes.

A ideia é usarmos o próprio ID do registro (gerado randomicamente pelo Postgres) como Token de Ativação.

```python title="./myapi/users/models.py"
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class UUIDUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    def __str__(self):
        return self.username


class ActivationToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UUIDUser, on_delete=models.CASCADE, related_name='activation_tokens')
    used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'ActivationToken for {self.user.username}'

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_used(self):
        return self.used_at is not None
```

E agora vamos criar essa migration:

```bash
python manage.py makemigrations users
```

## Preparando a infraestrutura para envio de e-mails

O Django possui já os módulos prontos para enviarmos e-mails. O método `send_mail` da biblioteca `django.core.main` já se encarrega de tudo, só precisamos ter as coisas configuradas no `settings.py`, mas já vamos chegar lá! Por enquanto, apenas para um cenário de testes, vamos usar o próprio backend do Django para simular esse envio, e criar os testes em uma mailbox que ele cria internamente. Depois a gente integra com um sistema real de e-mails.

Para abstrair um pouco esse envio de e-mails, vamos criar um arquivo `mailer.py` dentro de `infra`, com uma função `send_message()` para enviar e-mails:

```python title="./infra/mailer.py"
from django.core.mail import send_mail


def send_message(mailOptions):
    send_mail(
        mailOptions['subject'],
        mailOptions['body'],
        mailOptions['from'],
        mailOptions['to'],
        fail_silently=False,
    )
```

E agora vamos fazer com que no `POST` de criação de usuários, o sistema envie esse e-mail de ativação. Mas vamos abstrair isso dentro de um arquivo `services.py`, para que essa inteligência não fique dentro do endpoint. Vamos especular que existe uma função chamada `send_activation_email()` que vai fazer isso pra gente, e na rota faremos apenas isso:

```python title="./myapi/users/api.py" hl_lines="20-25"
@router.post('users', response=UserWithGroupsSchema, summary='Create user', description='Create a new user', auth=None)
def create_users(request, data: UserCreateSchema):
    # Pre-create validation: check username and email uniqueness
    if User.objects.filter(username=data.username).exists():
        logger.warning(f'Attempt to create user with existing username: {data.username}')
        raise ConflictError('Username already exists')
    if User.objects.filter(email=data.email).exists():
        logger.warning(f'Attempt to create user with existing email: {data.email}')
        raise ConflictError('Email already exists')

    user = User.objects.create_user(
        username=data.username,
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        password=data.password,
        is_active=False,
    )

    # Send activation email
    try:
        send_activation_email(user)
        logger.info(f'Activation email sent to {user.email}')
    except Exception as e:
        logger.error(f'Failed to send activation email to {user.email}: {e}')

    logger.info(f'User {user.username} (id={user.id}) created')
    return Response(UserWithGroupsSchema.from_orm(user), status=201)
```

E agora sim vamos criar o `services.py` com essa função:

```python title="./myapi/users/services.py"
from django.contrib.auth import get_user_model
from infra.mailer import send_message
from loguru import logger

User = get_user_model()

def send_activation_email(user, token_expiry_minutes=15):
    """
    Send activation email to user with link to activate account.

    Args:
        user: User instance
        token_expiry_minutes: Number of minutes until token expires (default: 15)
    """
    # Prepare email
    mail_options = {
        'subject': 'Ative sua conta',
        'body': f"""Olá {user.first_name or user.username},

Clique no link abaixo para ativar sua conta:
<TBD>

Este link expira em {token_expiry_minutes} minutos.

Se você não criou essa conta, ignore este email.
""",
        'from': 'contato@myapi.com',
        'to': [user.email],
    }

    try:
        send_message(mail_options)
        logger.info(f'Activation email sent to {user.email}')
    except Exception as e:
        logger.error(f'Error sending activation email to {user.email}: {e}')
        raise
```

!!! success

    Pronto, somente com isso, o sistema já está pronto para enviar e-mails, e já deveria estar enviando o e-mail de ativação (ainda que sem o link de ativação e sem o token)

## Testando o recebimento de e-mail

Vamos adicionar um teste no `test_create_users_success` para validar o recebimento do e-mail:

```python title="./myapi/users/tests/test_users.py"

@pytest.mark.django_db
def test_create_users_success(client):
    # Clear outbox
    mail.outbox = []

    user_payload = {
        'username': 'admin_new',
        'first_name': 'New',
        'last_name': 'Admin',
        'email': 'admin_new@admin.com',
        'password': 'myadminpassword',
    }
    response = client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )
    response_json = response.json()

    assert response.status_code == HTTPStatus.CREATED
    assert response_json['username'] == user_payload['username']

    # Assert activation email was sent
    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    print(f"Para: {email.to}")
    print(f"Assunto: {email.subject}")
    print(f"Corpo: {email.body}")
    assert email.subject == 'Ative sua conta'
```

Agora se rodarmos os testes, veremos isso:

```bash
2026-01-30 15:35:28.232 | INFO     | myapi.users.api:create_users:115 - Activation email sent to admin_new@admin.com
2026-01-30 15:35:28.232 | INFO     | myapi.users.api:create_users:119 - User admin_new (id=66b4c630-0398-4c0e-940b-1f9814f42311) created
Para: ['admin_new@admin.com']
Assunto: Ative sua conta
Corpo: Olá New,

Clique no link abaixo para ativar sua conta:
<TBD>

Este link expira em 15 minutos.

Se você não criou essa conta, ignore este email.
```

Sinal que o e-mail está chegando!

## Gerando o Token de Ativação

Agora o próximo passo é gerarmos o Token de ativação e gerar o link. Como optamos por usar o ID do registro no banco como token, basta criarmos um registro na tabela e pegar o ID que ele gerou. Para gerar um registro na tabela, podemos usar o model que criamos, assim:

```python
activation_token = ActivationToken.objects.create(
    user=user,
    expires_at=expires_at,
)
```

E para gerar o `expires_at`, podemos usar um timedelta somando 15 minutos ao tempo atual:

```python
expires_at = timezone.now() + timedelta(minutes=token_expiry_minutes)
```

Para gerar o link, precisaremos também do endereço do servidor, que será `http://localhost:3000` no ambiente de dev, ou `https://dominio.com` no ambiente de prod. Podemos controlar isso através da variável de ambiente `FRONTEND_FQDN`, que já temos definido no nosso `.env`.

Agora basta adicionarmos isso tudo na função `send_activation_token`. Vamos aproveitar e formatar um e-mail mais bonito em HTML.

```python title="./myapi/users/services.py" hl_lines="9-10 12-14 16-21 23-24 32"
def send_activation_email(user, token_expiry_minutes=15):
    """
    Send activation email to user with link to activate account.

    Args:
        user: User instance
        token_expiry_minutes: Number of minutes until token expires (default: 15)
    """
    # Get frontend domain from env
    frontend_fqdn = config('FRONTEND_FQDN', default='localhost:3000')

    # Determine protocol based on domain
    use_https = 'localhost' not in frontend_fqdn
    protocol = 'https' if use_https else 'http'

    # Create activation token record (id is the token)
    expires_at = timezone.now() + timedelta(minutes=token_expiry_minutes)
    activation_token = ActivationToken.objects.create(
        user=user,
        expires_at=expires_at,
    )

    # Build activation URL using the token id
    activation_url = f'{protocol}://{frontend_fqdn}/activate/{activation_token.id}'

    # Prepare email
    mail_options = {
        'subject': 'Ative sua conta',
        'body': f"""Olá {user.first_name or user.username},

Clique no link abaixo para ativar sua conta:
{activation_url}

Este link expira em {token_expiry_minutes} minutos.

Se você não criou essa conta, ignore este email.
""",
        'from': 'contato@myapi.com',
        'to': [user.email],
    }

    try:
        send_message(mail_options)
        logger.info(f'Activation email sent to {user.email}')
    except Exception as e:
        logger.error(f'Error sending activation email to {user.email}: {e}')
        raise
```

Vamos rodar o teste mais uma vez para ver como aparece o print do e-mail:

```bash
9:40:35 test.1 | 2026-02-02 09:40:35.293 | INFO     | myapi.users.api:create_users:115 - Activation email sent to admin_new@admin.com
09:40:35 test.1 | 2026-02-02 09:40:35.293 | INFO     | myapi.users.api:create_users:119 - User admin_new (id=4eda7895-49be-448f-b55c-8e0a6091628f) created
09:40:35 test.1 | Para: ['admin_new@admin.com']
09:40:35 test.1 | Assunto: Ative sua conta
09:40:35 test.1 | Corpo: Olá New,
09:40:35 test.1 |
09:40:35 test.1 | Clique no link abaixo para ativar sua conta:
09:40:35 test.1 | http://localhost:3000/activate/6339765d-7366-40e5-b99f-9ff3a602c135
09:40:35 test.1 |
09:40:35 test.1 | Este link expira em 15 minutos.
09:40:35 test.1 |
09:40:35 test.1 | Se você não criou essa conta, ignore este email.
```

!!! success

    Pronto! Agora já estamos enviando o e-mail de ativação da conta, com um link de ativação. Esse link vai abrir uma página que ainda precisamos desenolver, mas por hora, bastaría termos um endpoint em `api/v1/users/activate/{token_id}`, por exemplo, que faria a ativação a receber um request do tipo `PATCH`.

## Criando o endpoint de ativação

Agora vamos criar o endpoint na API que fará a ativação da conta. A ideia é recebermos um método PATCH em `api/v1/users/activate/{token_id}` que fará as seguintes ações:

1. Buscar o token na base e verificar se ele está válido (`expires_at` > data atual) e `used_at` como null
2. Pegar o user relacionado a esse token
3. Atualizar os campos `used_at` com a data atual
4. Atualizar o user com `is_active` como true

Agora vamos criar um cenário de teste com sucesso, onde depois de criarmos o usuário, fazemos um parsing do e-mail para pegar o ID do token que veio na URL, e depois enviamos um PATCH para o endpoint. O resultado esperado depois do PATCH é que o usuário esteja com o status is_active, e o token tenha uma data preenchida em used_at:

```python title="./myapi/users/tests/test_users.py"
@pytest.mark.django_db
def test_activate_user_success(client):
    """Test successful user account activation"""
    # Create a user
    user_payload = {
        'username': 'activate_test',
        'first_name': 'Activate',
        'last_name': 'Test',
        'email': 'activate@test.com',
        'password': 'testpassword',
    }
    response = client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )
    user_created = response.json()

    # User should be inactive
    assert user_created['is_active'] is False

    # Get the activation token from email
    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    match = re.search(r'/activate/([0-9a-fA-F-]{36})', email.body)
    activation_token_from_email = match.group(1) if match else None
    assert activation_token_from_email is not None, 'Activation token not found in email body'

    # Activate the user
    response = client.patch(
        f'/api/v1/users/activate/{activation_token_from_email}',
    )
    user_activated = response.json()

    assert response.status_code == HTTPStatus.OK
    assert user_activated['username'] == 'activate_test'
    assert user_activated['is_active'] is True

    # Check that token is marked as used
    activation_token = ActivationToken.objects.get(id=activation_token_from_email)
    assert activation_token.used_at is not None
```

Agora vamos criar esse endpoint na API. Ele basicamente vai chamar uma função auxiliar para verificar se o Token é válido, e se for, já atualizar o usuário para `is_active = True` e atualizar a data de `used_at` do token. Essa função ainda não existe, mas aqui na rota podemos especular que ela existe, e em seguida programar ela.

```python title="./mypi/users/api.py"
@router.patch(
    'users/activate/{token_id}',
    response=UserWithGroupsSchema,
    summary='Activate user account',
    description='Activate user account using activation token',
    auth=None,
)
def activate_user(request, token_id: uuid.UUID):
    user = verify_activation_token(str(token_id))

    if user is None:
        logger.warning(f'Attempt to activate with invalid token: token_id={token_id}')
        raise ValidationError('Invalid or expired activation token')

    logger.info(f'User {user.username} activated')
    return Response(UserWithGroupsSchema.from_orm(user), status=200)
```

Agora sim, vamos criar a função `verify_activation_token` dentro do `services.py`:

```python title="./myapi/users/services.py"
def verify_activation_token(token_id: str):
    """
    Verify activation token.

    Args:
        token_id: Activation token ID (UUID)

    Returns:
        User instance if token is valid and not expired
        None if token is invalid, expired, or already used
    """
    try:
        # Find activation token by id
        activation_token = ActivationToken.objects.get(
            id=token_id,
        )
    except ActivationToken.DoesNotExist:
        logger.warning(f'Invalid activation token: token_id={token_id}')
        return None

    # Check if token is expired
    if timezone.now() > activation_token.expires_at:
        logger.warning(f'Activation token expired for user {activation_token.user_id}')
        return None

    # Check if token is already used
    if activation_token.used_at is not None:
        logger.warning(f'Activation token already used for user {activation_token.user_id}')
        return None

    # Activate user
    user = activation_token.user
    user.is_active = True
    user.save()

    # Mark token as used
    activation_token.used_at = timezone.now()
    activation_token.save()

    logger.info(f'User {user.username} activated')
    return user
```

Pronto, agora já estamos conseguindo ativar o usuário com o Token gerado no e-mail de ativação. Vamos cobrir agora os cenários de ativação com um token inválido e com um token já utilizado. Em ambos deveríamos receber um erro `400 Bad Request`:

```python title="./myapi/users/tests/test_users.py"
@pytest.mark.django_db
def test_activate_user_invalid_token(client):
    """Test activation with invalid token"""
    # Try to activate with non-existent IDs
    token_id = uuid.uuid4()

    response = client.patch(f'/api/v1/users/activate/{token_id}')

    assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.django_db
def test_activate_user_already_used_token(client):
    """Test successful user account activation"""
    # Create a user
    user_payload = {
        'username': 'activate_test',
        'first_name': 'Activate',
        'last_name': 'Test',
        'email': 'activate@test.com',
        'password': 'testpassword',
    }
    response = client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )
    user_created = response.json()

    # User should be inactive
    assert user_created['is_active'] is False

    # Get the activation token from email
    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    match = re.search(r'/activate/([0-9a-fA-F-]{36})', email.body)
    activation_token_from_email = match.group(1) if match else None
    assert activation_token_from_email is not None, 'Activation token not found in email body'

    # Activate the user
    response = client.patch(
        f'/api/v1/users/activate/{activation_token_from_email}',
    )
    user_activated = response.json()

    assert response.status_code == HTTPStatus.OK
    assert user_activated['username'] == 'activate_test'
    assert user_activated['is_active'] is True

    # Check that token is marked as used
    activation_token = ActivationToken.objects.get(id=activation_token_from_email)
    assert activation_token.used_at is not None

    # Activate the user again
    response = client.patch(
        f'/api/v1/users/activate/{activation_token_from_email}',
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
```

Deu certo! Porque a gente já trata isso naquele erro customizado que criamos:

```python title="./myapi/users/api.py hl_lines="13"
@router.patch(
    'users/activate/{token_id}',
    response=UserWithGroupsSchema,
    summary='Activate user account',
    description='Activate user account using activation token',
    auth=None,
)
def activate_user(request, token_id: uuid.UUID):
    user = verify_activation_token(str(token_id))

    if user is None:
        logger.warning(f'Attempt to activate with invalid token: token_id={token_id}')
        raise ValidationError('Invalid or expired activation token')

    logger.info(f'User {user.username} activated')
    return Response(UserWithGroupsSchema.from_orm(user), status=200)
```

### Testando token expirado com o `freezegun`

Para testar um token expirado, vamos simular a passagem de tempo. Ou seja, temos que criar uma conta, avançar 16 minutos no tempo, e só então tentar ativar. A biblioteca `freezegun` do Python pode nos ajudar com isso. Vamos instalá-la como uma dependência de desenvolvimento

```bash
poettry add --group dev freezegun
```

E agora o nosso teste ficará assim:
```python title="./myapi/users/tests/test_users.py"
from freezegun import freeze_time
from datetime import timedelta

@pytest.mark.django_db
def test_activate_user_expired_token(client):
    """Test activation with expired token"""

    # Get current time
    now = timezone.now()

    # Create user at current time
    with freeze_time(now):
        user_payload = {
            'username': 'expire_test',
            'first_name': 'Expire',
            'last_name': 'Test',
            'email': 'expire@test.com',
            'password': 'testpassword',
        }
        response = client.post(
            '/api/v1/users',
            data=json.dumps(user_payload),
            content_type='application/json',
        )
        user_id = response.json()['id']

        # Get the activation token
        User = get_user_model()
        user = User.objects.get(id=user_id)
        activation_token = ActivationToken.objects.get(user=user)

    # Move 16 minutes to the future
    with freeze_time(now + timedelta(minutes=16)):
        # Try to activate with expired token
        response = client.patch(
            f'/api/v1/users/activate/{activation_token.id}',
            content_type='application/json',
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

        # User should still be inactive
        user.refresh_from_db()
        assert user.is_active is False
```

!!! success

    Agora sim temos o nosso sistema de ativação funcional e testado! O próximo passo é testarmos o login do usuário. Um usuário não ativo não deve conseguir fazer o login, e o usuário ativo deve conseguí-lo.

