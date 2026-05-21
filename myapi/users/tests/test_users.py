import json
import re
import uuid
from datetime import timedelta
from http import HTTPStatus

import pytest
from decouple import config
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from freezegun import freeze_time

from myapi.users.models import ActivationToken
from myapi.users.models import PasswordResetToken


@pytest.fixture
def admin_client(client):
    """Cliente autenticado como admin. O cookie é setado automaticamente pelo login."""
    client.post(
        '/api/v1/login',
        data=json.dumps({'username': config('DJANGO_ADMIN_USER'), 'password': config('DJANGO_ADMIN_PASSWORD')}),
        content_type='application/json',
    )
    return client


@pytest.fixture
def non_admin_client():
    """Cliente autenticado como usuário não-admin. Usa instância própria de Client
    para não conflitar com o admin_client quando ambos são usados no mesmo teste."""
    from django.test import Client
    c = Client()

    user_payload = {
        'username': 'new_user_non_admin',
        'first_name': 'New',
        'last_name': 'User',
        'email': 'user_new@admin.com',
        'password': 'myuserpassword',
    }
    c.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )

    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')
    user.is_active = True
    user.save()

    c.post(
        '/api/v1/login',
        data=json.dumps({'username': 'new_user_non_admin', 'password': 'myuserpassword'}),
        content_type='application/json',
    )
    return c


@pytest.mark.django_db
def test_list_users(admin_client):
    response = admin_client.get('/api/v1/users')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['count'] == 1
    assert data['items'][0]['username'] == 'admin'


@pytest.mark.django_db
def test_list_users_unauthorized(non_admin_client):
    response = non_admin_client.get('/api/v1/users')

    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_list_users_filter_by_id(admin_client):
    User = get_user_model()
    admin = User.objects.get(username=config('DJANGO_ADMIN_USER'))

    response = admin_client.get(f'/api/v1/users?id={admin.id}')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['items'][0]['username'] == config('DJANGO_ADMIN_USER')


@pytest.mark.django_db
def test_list_users_filter_by_username(admin_client):
    response = admin_client.get(f'/api/v1/users?username={config("DJANGO_ADMIN_USER")}')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['items'][0]['username'] == config('DJANGO_ADMIN_USER')


@pytest.mark.django_db
def test_get_user_detail_admin(admin_client):
    User = get_user_model()
    admin = User.objects.get(username=config('DJANGO_ADMIN_USER'))

    response = admin_client.get(f'/api/v1/users/{admin.id}')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['username'] == config('DJANGO_ADMIN_USER')


@pytest.mark.django_db
def test_get_user_detail_admin_to_other_user(admin_client, non_admin_client):
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    response = admin_client.get(f'/api/v1/users/{user.id}')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['username'] == 'new_user_non_admin'


@pytest.mark.django_db
def test_get_user_detail_user_to_himself_by_id(non_admin_client):
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    response = non_admin_client.get(f'/api/v1/users/{user.id}')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['username'] == 'new_user_non_admin'


@pytest.mark.django_db
def test_get_user_detail_user_to_other_user_fail(non_admin_client):
    User = get_user_model()
    user_admin = User.objects.get(username=config('DJANGO_ADMIN_USER'))

    response = non_admin_client.get(f'/api/v1/users/{user_admin.id}')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_create_users_success(client):
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
    assert response_json['is_active'] == False

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.subject == 'Ative sua conta'
    assert 'admin_new@admin.com' in email.to
    assert 'New' in email.body
    assert '/activate/' in email.body


@pytest.mark.django_db
def test_create_users_duplicated_username(admin_client):
    user_payload = {
        'username': 'admin',
        'first_name': 'New',
        'last_name': 'Admin',
        'email': 'admin_new@admin.com',
        'password': 'myadminpassword',
    }
    response = admin_client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )
    assert response.status_code == HTTPStatus.CONFLICT


@pytest.mark.django_db
def test_create_users_duplicated_email(admin_client):
    user_payload = {
        'username': 'admin_new',
        'first_name': 'New',
        'last_name': 'Admin',
        'email': 'admin@admin.com',
        'password': 'myadminpassword',
    }
    response = admin_client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )
    assert response.status_code == HTTPStatus.CONFLICT


@pytest.mark.django_db
def test_delete_user(admin_client):
    user_payload = {
        'username': 'admin_new',
        'first_name': 'New',
        'last_name': 'Admin',
        'email': 'admin_new@admin.com',
        'password': 'myadminpassword',
    }
    response = admin_client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )
    user_id = response.json()['id']

    response = admin_client.delete(f'/api/v1/users/{user_id}')
    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.mark.django_db
def test_delete_user_admin_to_other_user(admin_client, non_admin_client):
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    response = admin_client.delete(f'/api/v1/users/{user.id}')
    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.mark.django_db
def test_delete_user_to_himself(non_admin_client):
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    response = non_admin_client.delete(f'/api/v1/users/{user.id}')
    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.mark.django_db
def test_delete_user_to_other_user_fail(non_admin_client):
    User = get_user_model()
    user_admin = User.objects.get(username=config('DJANGO_ADMIN_USER'))

    response = non_admin_client.delete(f'/api/v1/users/{user_admin.id}')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_patch_user(admin_client):
    user_payload = {
        'username': 'admin_new',
        'first_name': 'New',
        'last_name': 'Admin',
        'email': 'admin_new@admin.com',
        'password': 'myadminpassword',
    }
    response = admin_client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )
    user_id = response.json()['id']

    patch_data = {
        'first_name': 'NewName',
        'email': 'newemail@admin.com',
    }

    response = admin_client.patch(
        f'/api/v1/users/{user_id}',
        data=json.dumps(patch_data),
        content_type='application/json',
    )

    response_json = response.json()
    assert response.status_code == HTTPStatus.OK
    assert response_json['first_name'] == 'NewName'
    assert response_json['email'] == 'newemail@admin.com'


@pytest.mark.django_db
def test_patch_user_admin_to_other_user(admin_client, non_admin_client):
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    patch_data = {
        'first_name': 'NewName',
        'email': 'newemail@admin.com',
    }

    response = admin_client.patch(
        f'/api/v1/users/{user.id}',
        data=json.dumps(patch_data),
        content_type='application/json',
    )
    response_json = response.json()
    assert response.status_code == HTTPStatus.OK
    assert response_json['first_name'] == 'NewName'
    assert response_json['email'] == 'newemail@admin.com'


@pytest.mark.django_db
def test_patch_user_to_himself(non_admin_client):
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    patch_data = {
        'first_name': 'NewName',
        'email': 'newemail@admin.com',
    }

    response = non_admin_client.patch(
        f'/api/v1/users/{user.id}',
        data=json.dumps(patch_data),
        content_type='application/json',
    )
    response_json = response.json()
    assert response.status_code == HTTPStatus.OK
    assert response_json['first_name'] == 'NewName'
    assert response_json['email'] == 'newemail@admin.com'


@pytest.mark.django_db
def test_patch_user_to_other_user_fail(non_admin_client):
    User = get_user_model()
    user_admin = User.objects.get(username=config('DJANGO_ADMIN_USER'))

    patch_data = {
        'first_name': 'NewName',
        'email': 'newemail@admin.com',
    }

    response = non_admin_client.patch(
        f'/api/v1/users/{user_admin.id}',
        data=json.dumps(patch_data),
        content_type='application/json',
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_change_password_success(non_admin_client):
    """Test successful password change"""
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    change_password_data = {
        'current_password': 'myuserpassword',
        'new_password': 'mynewpassword',
    }

    response = non_admin_client.patch(
        f'/api/v1/users/{user.id}/change-password',
        data=json.dumps(change_password_data),
        content_type='application/json',
    )

    assert response.status_code == HTTPStatus.OK
    response_json = response.json()
    assert response_json['username'] == 'new_user_non_admin'

    user.refresh_from_db()
    assert user.check_password('mynewpassword')
    assert not user.check_password('myuserpassword')


@pytest.mark.django_db
def test_change_password_wrong_current_password(non_admin_client):
    """Test password change with wrong current password"""
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    change_password_data = {
        'current_password': 'wrongpassword',
        'new_password': 'mynewpassword',
    }

    response = non_admin_client.patch(
        f'/api/v1/users/{user.id}/change-password',
        data=json.dumps(change_password_data),
        content_type='application/json',
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    response_json = response.json()
    assert 'incorrect' in response_json['message'].lower()

    user.refresh_from_db()
    assert user.check_password('myuserpassword')
    assert not user.check_password('mynewpassword')


@pytest.mark.django_db
def test_change_password_admin_to_other_user(admin_client, non_admin_client):
    """Test that admin can change another user's password"""
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    change_password_data = {
        'current_password': 'myuserpassword',
        'new_password': 'adminchangedpassword',
    }

    response = admin_client.patch(
        f'/api/v1/users/{user.id}/change-password',
        data=json.dumps(change_password_data),
        content_type='application/json',
    )

    assert response.status_code == HTTPStatus.OK

    user.refresh_from_db()
    assert user.check_password('adminchangedpassword')


@pytest.mark.django_db
def test_change_password_user_to_other_user_fail(non_admin_client):
    """Test that non-admin user cannot change another user's password"""
    User = get_user_model()
    user_admin = User.objects.get(username=config('DJANGO_ADMIN_USER'))

    change_password_data = {
        'current_password': config('DJANGO_ADMIN_PASSWORD'),
        'new_password': 'newevilpassword',
    }

    response = non_admin_client.patch(
        f'/api/v1/users/{user_admin.id}/change-password',
        data=json.dumps(change_password_data),
        content_type='application/json',
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED

    user_admin.refresh_from_db()
    assert user_admin.check_password(config('DJANGO_ADMIN_PASSWORD'))
    assert not user_admin.check_password('newevilpassword')


@pytest.mark.django_db
def test_activate_user_success(client):
    """Test successful user account activation"""
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

    assert user_created['is_active'] is False

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    match = re.search(r'/activate/([0-9a-fA-F-]{36})', email.body)
    activation_token_from_email = match.group(1) if match else None
    assert activation_token_from_email is not None, 'Activation token not found in email body'

    response = client.patch(f'/api/v1/users/activate/{activation_token_from_email}')
    user_activated = response.json()

    assert response.status_code == HTTPStatus.OK
    assert user_activated['username'] == 'activate_test'
    assert user_activated['is_active'] is True

    activation_token = ActivationToken.objects.get(id=activation_token_from_email)
    assert activation_token.used_at is not None


@pytest.mark.django_db
def test_activate_user_invalid_token(client):
    """Test activation with invalid token"""
    token_id = uuid.uuid4()
    response = client.patch(f'/api/v1/users/activate/{token_id}')
    assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.django_db
def test_activate_user_already_used_token(client):
    """Test successful user account activation"""
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

    assert user_created['is_active'] is False

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    match = re.search(r'/activate/([0-9a-fA-F-]{36})', email.body)
    activation_token_from_email = match.group(1) if match else None
    assert activation_token_from_email is not None, 'Activation token not found in email body'

    response = client.patch(f'/api/v1/users/activate/{activation_token_from_email}')
    user_activated = response.json()

    assert response.status_code == HTTPStatus.OK
    assert user_activated['username'] == 'activate_test'
    assert user_activated['is_active'] is True

    activation_token = ActivationToken.objects.get(id=activation_token_from_email)
    assert activation_token.used_at is not None

    response = client.patch(f'/api/v1/users/activate/{activation_token_from_email}')
    assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.django_db
def test_activate_user_expired_token(client):
    """Test activation with expired token"""
    now = timezone.now()

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

        User = get_user_model()
        user = User.objects.get(id=user_id)
        activation_token = ActivationToken.objects.get(user=user)

    with freeze_time(now + timedelta(minutes=16)):
        response = client.patch(
            f'/api/v1/users/activate/{activation_token.id}',
            content_type='application/json',
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

        user.refresh_from_db()
        assert user.is_active is False


@pytest.mark.django_db
def test_resend_activation_success(client):
    """Test successful resend of activation token with expired token"""
    mail.outbox = []
    now = timezone.now()

    with freeze_time(now):
        user_payload = {
            'username': 'resend_test',
            'first_name': 'Resend',
            'last_name': 'Test',
            'email': 'resend@test.com',
            'password': 'testpassword',
        }
        response = client.post(
            '/api/v1/users',
            data=json.dumps(user_payload),
            content_type='application/json',
        )
        user_id = response.json()['id']

        User = get_user_model()
        user = User.objects.get(id=user_id)
        old_activation_token = ActivationToken.objects.get(user=user)
        old_token_id = str(old_activation_token.id)

        mail.outbox = []

    with freeze_time(now + timedelta(minutes=16)):
        response = client.patch(
            f'/api/v1/users/activate/{old_token_id}',
            content_type='application/json',
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

        response = client.post(
            f'/api/v1/users/resend-activation/{old_token_id}',
            content_type='application/json',
        )
        response_json = response.json()

        assert response.status_code == HTTPStatus.OK
        assert response_json['username'] == 'resend_test'
        assert response_json['is_active'] is False

        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.subject == 'Ative sua conta'
        assert 'resend@test.com' in email.to

        match = re.search(r'/activate/([0-9a-fA-F-]{36})', email.body)
        new_activation_token_id = match.group(1) if match else None
        assert new_activation_token_id is not None, 'New activation token not found in email body'

        assert new_activation_token_id != old_token_id

        response = client.patch(
            f'/api/v1/users/activate/{old_token_id}',
            content_type='application/json',
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

        response = client.patch(
            f'/api/v1/users/activate/{new_activation_token_id}',
            content_type='application/json',
        )
        user_activated = response.json()

        assert response.status_code == HTTPStatus.OK
        assert user_activated['username'] == 'resend_test'
        assert user_activated['is_active'] is True


@pytest.mark.django_db
def test_resend_activation_with_valid_token(client):
    """Test that resend fails when token is still valid"""
    now = timezone.now()

    with freeze_time(now):
        user_payload = {
            'username': 'valid_token_test',
            'first_name': 'Valid',
            'last_name': 'Token',
            'email': 'validtoken@test.com',
            'password': 'testpassword',
        }
        response = client.post(
            '/api/v1/users',
            data=json.dumps(user_payload),
            content_type='application/json',
        )
        user_id = response.json()['id']

        User = get_user_model()
        user = User.objects.get(id=user_id)
        activation_token = ActivationToken.objects.get(user=user)

    with freeze_time(now + timedelta(minutes=5)):
        response = client.post(
            f'/api/v1/users/resend-activation/{activation_token.id}',
            content_type='application/json',
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.django_db
def test_resend_activation_with_already_used_token(client):
    """Test that resend fails when token has already been used"""
    now = timezone.now()

    with freeze_time(now):
        user_payload = {
            'username': 'used_token_test',
            'first_name': 'Used',
            'last_name': 'Token',
            'email': 'usedtoken@test.com',
            'password': 'testpassword',
        }
        response = client.post(
            '/api/v1/users',
            data=json.dumps(user_payload),
            content_type='application/json',
        )
        user_id = response.json()['id']

        User = get_user_model()
        user = User.objects.get(id=user_id)
        activation_token = ActivationToken.objects.get(user=user)

        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        match = re.search(r'/activate/([0-9a-fA-F-]{36})', email.body)
        token_from_email = match.group(1) if match else None

        client.patch(f'/api/v1/users/activate/{token_from_email}')

    with freeze_time(now + timedelta(minutes=16)):
        response = client.post(
            f'/api/v1/users/resend-activation/{activation_token.id}',
            content_type='application/json',
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.django_db
def test_resend_activation_with_already_active_user(client):
    """Test that resend fails when user is already activated"""
    now = timezone.now()

    with freeze_time(now):
        user_payload = {
            'username': 'already_active_test',
            'first_name': 'Already',
            'last_name': 'Active',
            'email': 'alreadyactive@test.com',
            'password': 'testpassword',
        }
        response = client.post(
            '/api/v1/users',
            data=json.dumps(user_payload),
            content_type='application/json',
        )
        user_id = response.json()['id']

        User = get_user_model()
        user = User.objects.get(id=user_id)
        activation_token = ActivationToken.objects.get(user=user)

        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        match = re.search(r'/activate/([0-9a-fA-F-]{36})', email.body)
        token_from_email = match.group(1) if match else None

        response = client.patch(f'/api/v1/users/activate/{token_from_email}')
        assert response.status_code == HTTPStatus.OK

    with freeze_time(now + timedelta(minutes=16)):
        response = client.post(
            f'/api/v1/users/resend-activation/{activation_token.id}',
            content_type='application/json',
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.django_db
def test_resend_activation_invalid_token(client):
    """Test that resend fails with invalid token ID"""
    token_id = uuid.uuid4()

    response = client.post(
        f'/api/v1/users/resend-activation/{token_id}',
        content_type='application/json',
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.django_db
def test_get_current_user_admin(admin_client):
    """Test that admin can get their own profile"""
    response = admin_client.get('/api/v1/me')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['username'] == config('DJANGO_ADMIN_USER')
    assert 'email' in data
    assert 'id' in data


@pytest.mark.django_db
def test_get_current_user_non_admin(non_admin_client):
    """Test that non-admin user can get their own profile"""
    response = non_admin_client.get('/api/v1/me')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['username'] == 'new_user_non_admin'
    assert data['email'] == 'user_new@admin.com'
    assert 'id' in data


##############
# Password Reset
##############
@pytest.mark.django_db
def test_request_password_reset_success(client):
    """Test successful password reset request"""
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

    mail.outbox.clear()

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
    """Test password reset request with non-existent email"""
    reset_payload = {'email': 'nonexistent@test.com'}
    response = client.post(
        '/api/v1/users/password-reset/request',
        data=json.dumps(reset_payload),
        content_type='application/json',
    )
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert 'message' in data
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_confirm_password_reset_success(client):
    """Test successful password reset confirmation"""
    user_payload = {
        'username': 'reset_confirm_test',
        'first_name': 'Reset',
        'last_name': 'Confirm',
        'email': 'resetconfirm@test.com',
        'password': 'testpassword',
    }
    client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )
    User = get_user_model()
    user = User.objects.get(username='reset_confirm_test')
    user.is_active = True
    user.save()

    reset_token = PasswordResetToken.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(minutes=15),
    )

    new_password_payload = {'new_password': 'newpassword123'}
    response = client.post(
        f'/api/v1/users/password-reset/{reset_token.id}/confirm',
        data=json.dumps(new_password_payload),
        content_type='application/json',
    )

    assert response.status_code == HTTPStatus.OK

    user.refresh_from_db()
    assert user.check_password('newpassword123')

    reset_token.refresh_from_db()
    assert reset_token.used_at is not None


@pytest.mark.django_db
def test_confirm_password_reset_invalid_token(client):
    """Test password reset confirmation with invalid token"""
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
    user_payload = {
        'username': 'reset_expire_test',
        'first_name': 'Reset',
        'last_name': 'Expire',
        'email': 'resetexpire@test.com',
        'password': 'testpassword',
    }
    client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )
    User = get_user_model()
    user = User.objects.get(username='reset_expire_test')
    user.is_active = True
    user.save()

    now = timezone.now()

    with freeze_time(now - timedelta(minutes=20)):
        reset_token = PasswordResetToken.objects.create(
            user=user,
            expires_at=now - timedelta(minutes=5),
        )

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
    user_payload = {
        'username': 'reset_used_test',
        'first_name': 'Reset',
        'last_name': 'Used',
        'email': 'resetused@test.com',
        'password': 'testpassword',
    }
    client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )
    User = get_user_model()
    user = User.objects.get(username='reset_used_test')
    user.is_active = True
    user.save()

    reset_token = PasswordResetToken.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(minutes=15),
        used_at=timezone.now(),
    )

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
    user_payload = {
        'username': 'validate_test',
        'first_name': 'Validate',
        'last_name': 'Test',
        'email': 'validate@test.com',
        'password': 'testpassword',
    }
    client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )
    User = get_user_model()
    user = User.objects.get(username='validate_test')

    reset_token = PasswordResetToken.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(minutes=15),
    )

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
    user_payload = {
        'username': 'validate_expire_test',
        'first_name': 'Validate',
        'last_name': 'Expire',
        'email': 'validateexpire@test.com',
        'password': 'testpassword',
    }
    client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )
    User = get_user_model()
    user = User.objects.get(username='validate_expire_test')

    now = timezone.now()

    with freeze_time(now - timedelta(minutes=20)):
        reset_token = PasswordResetToken.objects.create(
            user=user,
            expires_at=now - timedelta(minutes=5),
        )

    response = client.get(f'/api/v1/users/password-reset/{reset_token.id}/validate')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['valid'] is False
    assert 'expired' in data['message'].lower()


@pytest.mark.django_db
def test_validate_password_reset_token_already_used(client):
    """Test validation with already used token"""
    user_payload = {
        'username': 'validate_used_test',
        'first_name': 'Validate',
        'last_name': 'Used',
        'email': 'validateused@test.com',
        'password': 'testpassword',
    }
    client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )
    User = get_user_model()
    user = User.objects.get(username='validate_used_test')

    reset_token = PasswordResetToken.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(minutes=15),
        used_at=timezone.now(),
    )

    response = client.get(f'/api/v1/users/password-reset/{reset_token.id}/validate')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['valid'] is False
    assert 'used' in data['message'].lower()
