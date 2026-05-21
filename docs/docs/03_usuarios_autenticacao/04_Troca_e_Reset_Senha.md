# Implementando a troca e reset de senhas

Atualmente já temos um endpoint de `PATCH` de users configurado, e dessa forma o usuário consegue atualizar os seus dados, mas veja que o schema `UserPatchSchema` que criamos não possui o campo de senha, de forma que esse é um campo que ele não consegue atualizar com um simples `PATCH`. O ideal é que para troca de senha tenhamos que pedir a confirmação da senha antiga, e depois enviamos um e-mail informando que houve uma alteração na senha. Já para reset de senhas, teríamos que fazer por confirmação por email.

Por isso, vamos criar endpoints na nossa API dedicados a essa função:

- **PATCH** `api/v1/users/{id}/change-password`
- **POST**`api/v1/users/password-reset/request`
- **GET** `api/v1/users/password-reset/{token-id}/validate`
- **POST**`api/v1/users/password-reset/{token-id}/confirm`


## Criando a rota `change-password`

Como essa é uma rota para atualização de dados do usuário, sugiro pegarmos como base a rota de `PATCH` de `users/{id}`

```python title="./myapi/users/api.py"
@router.patch(
    'users/{id}/change-password',
    response=UserWithGroupsSchema,
    summary='Update user password',
    description='Update only password',
    auth=OwnerOrAdminAuth(),
)
def patch_user_password(request, id: uuid.UUID, payload: UserPatchPasswordSchema):
    try:
        user = User.objects.get(id=id)
    except User.DoesNotExist:
        logger.warning(f'Attempt to update non-existent user: {id}')
        raise NotFoundError('User not found')

    ## Fazer as validações necessárias e gerar um objeto de user atualizado

    try:
        user.save()
        logger.info(
            f'User {user.username} (id={id}) updated by {request.auth} - fields: {list(updated_fields.keys())}'
        )
        return Response(UserWithGroupsSchema.from_orm(user), status=200)
    except Exception as e:
        logger.error(f'Failed to update user: {e}')
        raise ServiceError('An unknow Service error ocurred when updating an user.')
```

E agora vamos criar esse novo schema:

```python title="./myapi/users/schemas.py"
class UserPatchPasswordSchema(Schema):
    current_password: str = Field(..., example='strongpassword')
    new_password: str = Field(..., example='strongpassword')
```

Certo, agora na função `patch_user_password`, podemos usar os métodos `check_password()` e `set_password` padrões do Django, e vem junto com o model `AbstractUser`! Muito mão na roda:

```python title="./myapi/users/api.py" hl_lines="15-22"
@router.patch(
    'users/{id}/change-password',
    response=UserWithGroupsSchema,
    summary='Update user password',
    description='Update password with current password verification',
    auth=OwnerOrAdminAuth(),
)
def patch_user_password(request, id: uuid.UUID, payload: UserPatchPasswordSchema):
    try:
        user = User.objects.get(id=id)
    except User.DoesNotExist:
        logger.warning(f'Attempt to update non-existent user: {id}')
        raise NotFoundError('User not found')

    # Validate current password
    if not user.check_password(payload.current_password):
        logger.warning(f'Failed password change attempt for user {user.username} - wrong current password')
        raise ValidationError('Current password is incorrect.')

    # Validate new password against Django's AUTH_PASSWORD_VALIDATORS
    try:
        validate_password(payload.new_password, user=user)
    except DjangoValidationError as e:
        raise ValidationError(', '.join(e.messages))

    user.set_password(payload.new_password)

    try:
        user.save()
        logger.info(f'User {user.username} (id={id}) changed password')
        return Response(UserWithGroupsSchema.from_orm(user), status=200)
    except Exception as e:
        logger.error(f'Failed to update password for user {user.username}: {e}')
        raise ServiceError('Failed to change password. Please try again later.')
```

!!! tip "Por que `validate_password` antes de `set_password`?"

    O `set_password()` do Django apenas faz o **hash** da senha — ele não verifica se a senha atende às regras configuradas em `AUTH_PASSWORD_VALIDATORS` (comprimento mínimo, senhas comuns, etc.). Sem a chamada explícita a `validate_password()`, qualquer senha seria aceita, incluindo `"123"`.

    O `validate_password()` lança `DjangoValidationError` se a senha não for válida. Por isso capturamos a exceção e lançamos nossa `ValidationError` customizada, que retorna um `400` com a mensagem de erro para o front-end.

    ```python
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError as DjangoValidationError

    try:
        validate_password(payload.new_password, user=user)
    except DjangoValidationError as e:
        raise ValidationError(', '.join(e.messages))

    user.set_password(payload.new_password)
    ```

E agora vamos cobrir isso com testes:

- Troca de senha com sucesso pelo próprio usuário
- Troca de senha sem sucesso passando a senha atual incorreta
- Troca de senha com sucesso pelo admin
- Troca de senha sem sucesso de um usuário para outro usuário

```python title="./myapi/users/tests/test_users.py"
@pytest.mark.django_db
def test_change_password_success(client, create_non_admin_access_token):
    """Test successful password change"""
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    change_password_data = {
        'current_password': 'myuserpassword',
        'new_password': 'mynewpassword',
    }

    response = client.patch(
        f'/api/v1/users/{user.id}/change-password',
        data=json.dumps(change_password_data),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {create_non_admin_access_token}',
    )

    assert response.status_code == HTTPStatus.OK
    response_json = response.json()
    assert response_json['username'] == 'new_user_non_admin'

    # Verify the password was actually changed
    user.refresh_from_db()
    assert user.check_password('mynewpassword')
    assert not user.check_password('myuserpassword')


@pytest.mark.django_db
def test_change_password_wrong_current_password(client, create_non_admin_access_token):
    """Test password change with wrong current password"""
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    change_password_data = {
        'current_password': 'wrongpassword',
        'new_password': 'mynewpassword',
    }

    response = client.patch(
        f'/api/v1/users/{user.id}/change-password',
        data=json.dumps(change_password_data),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {create_non_admin_access_token}',
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    response_json = response.json()
    assert 'incorrect' in response_json['message'].lower()

    # Verify password was NOT changed
    user.refresh_from_db()
    assert user.check_password('myuserpassword')
    assert not user.check_password('mynewpassword')


@pytest.mark.django_db
def test_change_password_admin_to_other_user(client, create_admin_access_token, create_non_admin_access_token):
    """Test that admin can change another user's password"""
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    change_password_data = {
        'current_password': 'myuserpassword',
        'new_password': 'adminchangedpassword',
    }

    response = client.patch(
        f'/api/v1/users/{user.id}/change-password',
        data=json.dumps(change_password_data),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {create_admin_access_token}',
    )

    assert response.status_code == HTTPStatus.OK

    # Verify the password was changed
    user.refresh_from_db()
    assert user.check_password('adminchangedpassword')


@pytest.mark.django_db
def test_change_password_user_to_other_user_fail(client, create_non_admin_access_token):
    """Test that non-admin user cannot change another user's password"""
    User = get_user_model()
    user_admin = User.objects.get(username=config('DJANGO_ADMIN_USER'))

    change_password_data = {
        'current_password': config('DJANGO_ADMIN_PASSWORD'),
        'new_password': 'newevilpassword',
    }

    response = client.patch(
        f'/api/v1/users/{user_admin.id}/change-password',
        data=json.dumps(change_password_data),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {create_non_admin_access_token}',
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Verify admin password was NOT changed
    user_admin.refresh_from_db()
    assert user_admin.check_password(config('DJANGO_ADMIN_PASSWORD'))
    assert not user_admin.check_password('newevilpassword')
```

## Criando as rotas de `password-reset`

O reset de senha é um pouco mais complexo, porque temos que fazer parecido com o sistema de ativação de conta. Ou seja, o usuário solicita o reset passando o e-mail dele, o sistema gera um token com expiração de 15 minutos e manda por e-mail, o usuário entra no link de reset de senha, define a nova senha e salva.

### Criando uma nova tabela `PasswordResetToken`

O primeiro passo é criarmos uma nova tabela na base, que podemos chamar de PasswordResetToken. Vamos definir uma nova classe nos models de `users`, que será basicamente a mesma coisa que o ActivationToken:

```python title="./myapi/users/models.py"
class PasswordResetToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UUIDUser, on_delete=models.CASCADE, related_name='password_reset_tokens')
    used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'PasswordResetToken for {self.user.username}'

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_used(self):
        return self.used_at is not None
```

E agora gerar a migration:

```bash
python3 manage.py makemigrations users
```

### Criando o endpoint `users/password-reset/request`

Esse será o endpoint que será chamado pelo front quando o usuário solicitar um password reset, e ele deverá receber como payload o `e-mail` do usuário (poderia ser o username também, aí vai do seu gosto). Aí a ideia é gerarmos um token e armazenarmos na base (exatamente como é feito com o de ativação, depois que o usuário cria um cadastro), e enviamos esse e-mail para o usuário.

Vamos criar o schema `PasswordResetRequestSchema`:

```python title="./myapi/users/schemas.py"
class PasswordResetRequestSchema(Schema):
    email: str = Field(..., example='user@email.com')
```

E agora a rota, bem parecida com a rota do `POST` de `/users`, só que antes temos que validar se o usuário existe, filtrando pelo e-mail, e depois chamamos a função `send_password_reset_email()`, que ainda vamos criar:

```python title="./myapi/users/api.py"
@router.post(
    'users/password-reset/request',
    response={200: dict},
    summary='Request password reset',
    description='Request a password reset token via email',
    auth=None,
)
def request_password_reset(request, data: PasswordResetRequestSchema):
    try:
        user = User.objects.get(email=data.email)
    except User.DoesNotExist:
        # For security, don't reveal if email exists
        logger.warning(f'Password reset requested for non-existent email: {data.email}')
        return Response({'message': 'If email exists, a reset link will be sent'}, status=200)

    # Send password reset email (which creates the token internally)
    try:
        send_password_reset_email(user)
        logger.info(f'Password reset email sent to {user.email}')
    except Exception as e:
        logger.error(f'Failed to send password reset email to {user.email}: {e}')

    logger.info(f'User {user.username} requested password reset')
    return Response({'message': 'If email exists, a reset link will be sent'}, status=200)
```

A função `send_password_reset_email` também será nos moldes da `send_activation_email`, pois geraremos um token com expiração de 15 minutos, armazenaremos na base, e enviaremos um e-mail para o usuário:

```python title="./myapi/users/services.py"
def send_password_reset_email(user, token_expiry_minutes=15):
    """
    Send password reset email to user with link to reset password.

    Args:
        user: User instance
        token_expiry_minutes: Number of minutes until token expires (default: 15)
    """
    # Get frontend domain from env
    frontend_fqdn = config('FRONTEND_FQDN', default='localhost:3000')

    # Determine protocol based on domain
    use_https = 'localhost' not in frontend_fqdn
    protocol = 'https' if use_https else 'http'

    # Create password reset token record (id is the token)
    expires_at = timezone.now() + timedelta(minutes=token_expiry_minutes)
    reset_token = PasswordResetToken.objects.create(
        user=user,
        expires_at=expires_at,
    )

    # Build password reset URL using the token id
    reset_url = f'{protocol}://{frontend_fqdn}/password-reset/{reset_token.id}'

    # Prepare email with HTML formatting
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto;">
                <h2>Redefinir Senha</h2>
                <p>Olá <strong>{user.first_name or user.username}</strong>,</p>
                <p>Recebemos uma solicitação para redefinir sua senha. Clique no link abaixo:</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" style="background-color: #28a745; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Redefinir Senha
                    </a>
                </p>
                <p style="font-size: 14px; color: #666;">
                    Ou copie este link no seu navegador:<br>
                    <code style="background-color: #f4f4f4; padding: 5px; border-radius: 3px; word-break: break-all;">
                        {reset_url}
                    </code>
                </p>
                <p style="font-size: 12px; color: #999;">
                    Este link expira em <strong>{token_expiry_minutes} minutos</strong>.
                </p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="font-size: 12px; color: #999;">
                    Se você não solicitou esta redefinição, ignore este email.
                </p>
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; text-align: center;">
                    <p style="font-size: 12px; color: #666; margin: 5px 0;">
                        <strong>Equipe Django Ninja API Boilerplate</strong><br>
                        Email: <a href="mailto:djangoninja.api@gmail.com" style="color: #28a745; text-decoration: none;">djangoninja.api@gmail.com</a>
                    </p>
                </div>
            </div>
        </body>
    </html>
    """

    # Prepare email
    mail_options = {
        'subject': 'Redefinir sua senha',
        'body': html_body,
        'from': 'contato@myapi.com',
        'to': [user.email],
    }

    try:
        send_message(mail_options)
        logger.info(f'Password reset email sent to {user.email}')
    except Exception as e:
        logger.error(f'Error sending password reset email to {user.email}: {e}')
        raise ServiceError('An error ocurred when sending the e-mail')
```

### Criando o endpoint `users/password-reset/{token_id}/validate`

Esse endpoint receberá um GET apenas para validar se o token que o usuário tem é válido, e caso seja, o front-end abrirá o formulário para ele de fato fazer a alteração da senha.

```python title="./myapi/users/api.py"
@router.get(
    'users/password-reset/{token_id}/validate',
    response={200: dict},
    summary='Validate password reset token',
    description='Check if password reset token is valid and not expired',
    auth=None,
)
def validate_password_reset(request, token_id: uuid.UUID):
    result = validate_password_reset_token(str(token_id))
    return Response(result, status=200)
```

A lógica do `validade_password_reset_token` será implementada no `services.py`:

```python title="./myapi/users/services.py"
def validate_password_reset_token(token_id: str):
    """
    Validate password reset token without marking it as used.

    Args:
        token_id: Password reset token ID (UUID)

    Returns:
        Dictionary with validation result: {valid: bool, message: str}
    """
    try:
        reset_token = PasswordResetToken.objects.get(id=token_id)
    except PasswordResetToken.DoesNotExist:
        logger.warning(f'Attempt to validate non-existent token: token_id={token_id}')
        return {'valid': False, 'message': 'Token not found'}

    # Check if token is expired
    if timezone.now() > reset_token.expires_at:
        logger.warning(f'Attempt to validate expired token: token_id={token_id}')
        return {'valid': False, 'message': 'Token has expired'}

    # Check if token is already used
    if reset_token.used_at is not None:
        logger.warning(f'Attempt to validate already used token: token_id={token_id}')
        return {'valid': False, 'message': 'Token has already been used'}

    logger.info(f'Token validation successful: token_id={token_id}')
    return {'valid': True, 'message': 'Token is valid'}
```

### Criando o endpoint `users/password-reset/{token_id}/confirm`

Esse é o endpoint que fará a validação do token de reset de senha, e já deverá receber no payload a senha nova. Caso ele valide que o token é válido, faremos a atualização da senha do usuário.

Vamos criar essa rota de forma muito similar à de `users/activate/{token_id}`, só que chamaremos uma função `confirm_password_reset_token`, que ainda iremos criar, e receberemos a senha nova no payload. Para isso, precisamos primeiro criar o schema:

```python title="./myapi/users/schemas.py"
class PasswordResetConfirmSchema(Schema):
    new_password: str = Field(..., example='strongpassword')
```

```python title="./myapi/users/api.py"
@router.post(
    'users/password-reset/{token_id}/confirm',
    response={200: dict},
    summary='Confirm password reset',
    description='Confirm password reset and set new password',
    auth=None,
)
def confirm_password_reset(request, token_id: uuid.UUID, payload: PasswordResetConfirmSchema):
    user = confirm_password_reset_token(str(token_id))

    if user is None:
        logger.warning(f'Attempt to change password with invalid token: token_id={token_id}')
        raise ValidationError('Invalid password reset token.')

    # Validate new password against Django's AUTH_PASSWORD_VALIDATORS
    try:
        validate_password(payload.new_password, user=user)
    except DjangoValidationError as e:
        raise ValidationError(', '.join(e.messages))

    user.set_password(payload.new_password)
    try:
        user.save()
        logger.info(f'User {user.username} (id={user.id}) changed password')
        return Response({'message': 'Password changed successfully'}, status=200)
    except Exception as e:
        logger.error(f'Failed to update password for user {user.username}: {e}')
        raise ServiceError('Failed to change password. Please try again later.')
```

E agora vamos criar a `confirm_password_reset_token`,

```python title="./myapi/users/services.py"
def confirm_password_reset_token(token_id: str):
    """
    Verify password reset token, mark it as used, and return the associated user.

    Raises ValidationError if token is not found, expired, or already used.
    """
    try:
        password_reset_token = PasswordResetToken.objects.get(id=token_id)
    except PasswordResetToken.DoesNotExist:
        logger.warning(f'Attempt to change password with invalid token: token_id={token_id}')
        raise ValidationError('Password reset token not found')

    user = password_reset_token.user

    if timezone.now() > password_reset_token.expires_at:
        logger.warning(f'Password reset token is expired: token_id={token_id}')
        raise ValidationError('This link is expired, please request a new one')

    if password_reset_token.used_at is not None:
        logger.warning(f'Password reset token already used for user {password_reset_token.user_id}')
        raise ValidationError('This link was already used, please request a new one')

    password_reset_token.used_at = timezone.now()
    password_reset_token.save()

    return user
```

### Criando os testes

Bom, agora só falta cobrirmos os casos de teste:

- Envio do e-mail de reset de senhas com sucesso
- Não envio do email no caso de o usuário não existir
- Reset de senha com sucesso passando um token válido
- Reset de senha sem sucesso passando um token inválido
- Reset de senha sem sucesso passando um token expirado
- Reset de senha sem sucesso passando um token já utilizado
- Validação com sucesso de um token válido
- Validação sem sucesso de um token inválido
- Validação sem sucesso de um token expirado
- Validação sem sucesso de um token já utilizado

```python title="./myapi/users/tests/test_users.py"
##############
# Password Reset
##############
@pytest.mark.django_db
def test_request_password_reset_success(client):
    """Test successful password reset request"""
    # Create a user
    user_payload = {
        'username': 'reset_test',
        'first_name': 'Reset',
        'last_name': 'Test',
        'email': 'reset@test.com',
        'password': 'testpassword',
    }
    response = client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )
    assert response.status_code == HTTPStatus.CREATED

    # Clear mailbox
    mail.outbox.clear()

    # Request password reset
    reset_payload = {'email': 'reset@test.com'}
    response = client.post(
        '/api/v1/users/password-reset/request',
        data=json.dumps(reset_payload),
        content_type='application/json',
    )
    data = response.json()
    assert 'message' in data
    assert response.status_code == HTTPStatus.OK
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_request_password_reset_non_existent_email(client):
    """Test password reset request with non-existent email """
    reset_payload = {'email': 'nonexistent@test.com'}
    response = client.post(
        '/api/v1/users/password-reset/request',
        data=json.dumps(reset_payload),
        content_type='application/json',
    )
    data = response.json()

    # Should return same message for security (no email enumeration)
    assert response.status_code == HTTPStatus.OK
    assert 'message' in data
    # Should not send email
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_confirm_password_reset_success(client):
    """Test successful password reset confirmation"""

    # Create and activate a user
    user_payload = {
        'username': 'reset_confirm_test',
        'first_name': 'Reset',
        'last_name': 'Confirm',
        'email': 'resetconfirm@test.com',
        'password': 'testpassword',
    }
    response = client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )
    User = get_user_model()
    user = User.objects.get(username='reset_confirm_test')
    user.is_active = True
    user.save()

    # Create a password reset token
    reset_token = PasswordResetToken.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(minutes=15),
    )

    # Confirm password reset
    new_password_payload = {'new_password': 'newpassword123'}
    response = client.post(
        f'/api/v1/users/password-reset/{reset_token.id}/confirm',
        data=json.dumps(new_password_payload),
        content_type='application/json',
    )

    assert response.status_code == HTTPStatus.OK

    # Check that password was changed
    user.refresh_from_db()
    assert user.check_password('newpassword123')

    # Check that token is marked as used
    reset_token.refresh_from_db()
    assert reset_token.used_at is not None


@pytest.mark.django_db
def test_confirm_password_reset_invalid_token(client):
    """Test password reset confirmation with invalid token"""
    # Try to confirm with non-existent token
    token_id = uuid.uuid4()
    new_password_payload = {'new_password': 'newpassword123'}

    response = client.post(
        f'/api/v1/users/password-reset/{token_id}/confirm',
        data=json.dumps(new_password_payload),
        content_type='application/json',
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.django_db
def test_confirm_password_reset_expired_token(client):
    """Test password reset confirmation with expired token"""

    # Create and activate a user
    user_payload = {
        'username': 'reset_expire_test',
        'first_name': 'Reset',
        'last_name': 'Expire',
        'email': 'resetexpire@test.com',
        'password': 'testpassword',
    }
    response = client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )
    User = get_user_model()
    user = User.objects.get(username='reset_expire_test')
    user.is_active = True
    user.save()

    # Get current time
    now = timezone.now()

    # Create an expired password reset token
    with freeze_time(now - timedelta(minutes=20)):
        reset_token = PasswordResetToken.objects.create(
            user=user,
            expires_at=now - timedelta(minutes=5),  # Already expired
        )

    # Try to confirm with expired token
    new_password_payload = {'new_password': 'newpassword123'}
    response = client.post(
        f'/api/v1/users/password-reset/{reset_token.id}/confirm',
        data=json.dumps(new_password_payload),
        content_type='application/json',
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.django_db
def test_confirm_password_reset_already_used_token(client):
    """Test password reset confirmation with already used token"""

    # Create and activate a user
    user_payload = {
        'username': 'reset_used_test',
        'first_name': 'Reset',
        'last_name': 'Used',
        'email': 'resetused@test.com',
        'password': 'testpassword',
    }
    response = client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )
    User = get_user_model()
    user = User.objects.get(username='reset_used_test')
    user.is_active = True
    user.save()

    # Create a password reset token and mark as used
    reset_token = PasswordResetToken.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(minutes=15),
        used_at=timezone.now(),
    )

    # Try to confirm with already used token
    new_password_payload = {'new_password': 'newpassword123'}
    response = client.post(
        f'/api/v1/users/password-reset/{reset_token.id}/confirm',
        data=json.dumps(new_password_payload),
        content_type='application/json',
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.django_db
def test_validate_password_reset_token_success(client):
    """Test successful password reset token validation"""

    # Create and activate a user
    user_payload = {
        'username': 'validate_test',
        'first_name': 'Validate',
        'last_name': 'Test',
        'email': 'validate@test.com',
        'password': 'testpassword',
    }
    response = client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )
    User = get_user_model()
    user = User.objects.get(username='validate_test')

    # Create a valid password reset token
    reset_token = PasswordResetToken.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(minutes=15),
    )

    # Validate token
    response = client.get(f'/api/v1/users/password-reset/{reset_token.id}/validate')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['valid'] is True
    assert 'message' in data


@pytest.mark.django_db
def test_validate_password_reset_token_invalid(client):
    """Test validation with non-existent token"""
    token_id = uuid.uuid4()

    response = client.get(f'/api/v1/users/password-reset/{token_id}/validate')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['valid'] is False
    assert 'message' in data


@pytest.mark.django_db
def test_validate_password_reset_token_expired(client):
    """Test validation with expired token"""

    # Create and activate a user
    user_payload = {
        'username': 'validate_expire_test',
        'first_name': 'Validate',
        'last_name': 'Expire',
        'email': 'validateexpire@test.com',
        'password': 'testpassword',
    }
    response = client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )
    User = get_user_model()
    user = User.objects.get(username='validate_expire_test')

    # Get current time
    now = timezone.now()

    # Create an expired password reset token
    with freeze_time(now - timedelta(minutes=20)):
        reset_token = PasswordResetToken.objects.create(
            user=user,
            expires_at=now - timedelta(minutes=5),  # Already expired
        )

    # Try to validate expired token
    response = client.get(f'/api/v1/users/password-reset/{reset_token.id}/validate')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['valid'] is False
    assert 'expired' in data['message'].lower()


@pytest.mark.django_db
def test_validate_password_reset_token_already_used(client):
    """Test validation with already used token"""

    # Create and activate a user
    user_payload = {
        'username': 'validate_used_test',
        'first_name': 'Validate',
        'last_name': 'Used',
        'email': 'validateused@test.com',
        'password': 'testpassword',
    }
    response = client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )
    User = get_user_model()
    user = User.objects.get(username='validate_used_test')

    # Create a password reset token and mark as used
    reset_token = PasswordResetToken.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(minutes=15),
        used_at=timezone.now(),
    )

    # Try to validate already used token
    response = client.get(f'/api/v1/users/password-reset/{reset_token.id}/validate')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['valid'] is False
    assert 'used' in data['message'].lower()
```

!!! success

    Terminamos os nossos endpoints de troca e reset de senha, agora o front-end já pode consumir essas rotas e fazer a implementação das telas.
