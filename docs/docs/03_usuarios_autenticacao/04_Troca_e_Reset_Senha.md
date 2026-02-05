# Implementando a troca e reset de senhas

Atualmente já temos um endpoint de `PATCH` de users configurado, e dessa forma o usuário consegue atualizar os seus dados, mas veja que o schema `UserPatchSchema` que criamos não possui o campo de senha, de forma que esse é um campo que ele não consegue atualizar com um simples `PATCH`. O ideal é que para troca de senha tenhamos que pedir a confirmação da senha antiga, e depois enviamos um e-mail informando que houve uma alteração na senha. Já para reset de senhas, teríamos que fazer por confirmação por email.

Por isso, vamos criar endpoints na nossa API dedicados a essa função:

- `api/v1/users/{id}/change-password`
- `api/v1/users/reset-password/{token-id}`

O primeiro será um simples `PATCH` no usuário, e o segundo, como o usuário não está logado, faremos mediante a um token, similar à forma como fazemos a ativação.

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

    # Set new password (this hashes it properly)
    user.set_password(payload.new_password)

    try:
        user.save()
        logger.info(f'User {user.username} (id={id}) changed password')
        return Response(UserWithGroupsSchema.from_orm(user), status=200)
    except Exception as e:
        logger.error(f'Failed to update password for user {user.username}: {e}')
        raise ServiceError('Failed to change password. Please try again later.')
```

E agora vamos cobrir isso com testes:
* Troca de senha com sucesso pelo próprio usuário
* Troca de senha sem sucesso passando a senha atual incorreta
* Troca de senha com sucesso pelo admin
* Troca de senha sem sucesso de um usuário para outro usuário

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

## Criando a rota `reset-password`