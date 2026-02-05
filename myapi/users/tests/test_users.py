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
def test_list_users(client, create_admin_access_token):
    response = client.get('/api/v1/users', HTTP_AUTHORIZATION=f'Bearer {create_admin_access_token}')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['count'] == 1
    assert data['items'][0]['username'] == 'admin'


@pytest.mark.django_db
def test_list_users_unauthorized(client, create_non_admin_access_token):
    response = client.get('/api/v1/users', HTTP_AUTHORIZATION=f'Bearer {create_non_admin_access_token}')

    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_list_users_filter_by_id(client, create_admin_access_token):
    User = get_user_model()
    admin = User.objects.get(username=config('DJANGO_ADMIN_USER'))

    response = client.get(f'/api/v1/users?id={admin.id}', HTTP_AUTHORIZATION=f'Bearer {create_admin_access_token}')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['items'][0]['username'] == config('DJANGO_ADMIN_USER')


@pytest.mark.django_db
def test_list_users_filter_by_username(client, create_admin_access_token):
    response = client.get(
        f'/api/v1/users?username={config("DJANGO_ADMIN_USER")}',
        HTTP_AUTHORIZATION=f'Bearer {create_admin_access_token}',
    )
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['items'][0]['username'] == config('DJANGO_ADMIN_USER')


@pytest.mark.django_db
def test_get_user_detail_admin(client, create_admin_access_token):
    User = get_user_model()
    admin = User.objects.get(username=config('DJANGO_ADMIN_USER'))

    response = client.get(f'/api/v1/users/{admin.id}', HTTP_AUTHORIZATION=f'Bearer {create_admin_access_token}')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['username'] == config('DJANGO_ADMIN_USER')


@pytest.mark.django_db
def test_get_user_detail_admin_to_other_user(client, create_admin_access_token, create_non_admin_access_token):
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    response = client.get(f'/api/v1/users/{user.id}', HTTP_AUTHORIZATION=f'Bearer {create_admin_access_token}')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['username'] == 'new_user_non_admin'


@pytest.mark.django_db
def test_get_user_detail_user_to_himself_by_id(client, create_non_admin_access_token):
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    response = client.get(f'/api/v1/users/{user.id}', HTTP_AUTHORIZATION=f'Bearer {create_non_admin_access_token}')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['username'] == 'new_user_non_admin'


@pytest.mark.django_db
def test_get_user_detail_user_to_himself_by_username(client, create_non_admin_access_token):
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    response = client.get(
        f'/api/v1/users/username/{user.username}', HTTP_AUTHORIZATION=f'Bearer {create_non_admin_access_token}'
    )
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['username'] == 'new_user_non_admin'


@pytest.mark.django_db
def test_get_user_detail_user_to_other_user_fail(client, create_non_admin_access_token):
    User = get_user_model()
    user_admin = User.objects.get(username=config('DJANGO_ADMIN_USER'))

    response = client.get(
        f'/api/v1/users/{user_admin.id}', HTTP_AUTHORIZATION=f'Bearer {create_non_admin_access_token}'
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


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
    assert response_json['is_active'] == False

    # Assert activation email was sent
    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.subject == 'Ative sua conta'
    assert 'admin_new@admin.com' in email.to
    assert 'New' in email.body
    assert '/activate/' in email.body


@pytest.mark.django_db
def test_create_users_duplicated_username(client, create_admin_access_token):
    user_payload = {
        'username': 'admin',
        'first_name': 'New',
        'last_name': 'Admin',
        'email': 'admin_new@admin.com',
        'password': 'myadminpassword',
    }
    response = client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {create_admin_access_token}',
    )
    assert response.status_code == HTTPStatus.CONFLICT


@pytest.mark.django_db
def test_create_users_duplicated_email(client, create_admin_access_token):
    user_payload = {
        'username': 'admin_new',
        'first_name': 'New',
        'last_name': 'Admin',
        'email': 'admin@admin.com',
        'password': 'myadminpassword',
    }
    response = client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {create_admin_access_token}',
    )
    assert response.status_code == HTTPStatus.CONFLICT


@pytest.mark.django_db
def test_delete_user(client, create_admin_access_token):
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
        HTTP_AUTHORIZATION=f'Bearer {create_admin_access_token}',
    )
    user_id = response.json()['id']

    response = client.delete(f'/api/v1/users/{user_id}', HTTP_AUTHORIZATION=f'Bearer {create_admin_access_token}')
    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.mark.django_db
def test_delete_user_admin_to_other_user(client, create_admin_access_token, create_non_admin_access_token):
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    response = client.delete(f'/api/v1/users/{user.id}', HTTP_AUTHORIZATION=f'Bearer {create_admin_access_token}')
    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.mark.django_db
def test_delete_user_to_himself(client, create_non_admin_access_token):
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    response = client.delete(f'/api/v1/users/{user.id}', HTTP_AUTHORIZATION=f'Bearer {create_non_admin_access_token}')
    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.mark.django_db
def test_delete_user_to_other_user_fail(client, create_non_admin_access_token):
    User = get_user_model()
    user_admin = User.objects.get(username=config('DJANGO_ADMIN_USER'))

    response = client.delete(
        f'/api/v1/users/{user_admin.id}', HTTP_AUTHORIZATION=f'Bearer {create_non_admin_access_token}'
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_patch_user(client, create_admin_access_token):
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
        HTTP_AUTHORIZATION=f'Bearer {create_admin_access_token}',
    )
    user_id = response.json()['id']

    patch_data = {
        'first_name': 'NewName',
        'email': 'newemail@admin.com',
    }

    response = client.patch(
        f'/api/v1/users/{user_id}',
        data=json.dumps(patch_data),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {create_admin_access_token}',
    )

    response_json = response.json()
    assert response.status_code == HTTPStatus.OK
    assert response_json['first_name'] == 'NewName'
    assert response_json['email'] == 'newemail@admin.com'


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


@pytest.mark.django_db
def test_resend_activation_success(client):
    """Test successful resend of activation token with expired token"""
    # Clear outbox
    mail.outbox = []

    # Get current time
    now = timezone.now()

    # Create user at current time
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

        # Get the activation token
        User = get_user_model()
        user = User.objects.get(id=user_id)
        old_activation_token = ActivationToken.objects.get(user=user)
        old_token_id = str(old_activation_token.id)

        # Clear outbox to get only the resend email
        mail.outbox = []

    # Move 16 minutes to the future (token expired)
    with freeze_time(now + timedelta(minutes=16)):
        # Try to activate with expired token - should fail
        response = client.patch(
            f'/api/v1/users/activate/{old_token_id}',
            content_type='application/json',
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

        # Request a new activation token
        response = client.post(
            f'/api/v1/users/resend-activation/{old_token_id}',
            content_type='application/json',
        )
        response_json = response.json()

        assert response.status_code == HTTPStatus.OK
        assert response_json['username'] == 'resend_test'
        assert response_json['is_active'] is False

        # Check that a new activation email was sent
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.subject == 'Ative sua conta'
        assert 'resend@test.com' in email.to

        # Extract the new token from the email
        match = re.search(r'/activate/([0-9a-fA-F-]{36})', email.body)
        new_activation_token_id = match.group(1) if match else None
        assert new_activation_token_id is not None, 'New activation token not found in email body'

        # Verify the new token is different from the old one
        assert new_activation_token_id != old_token_id

        # Try to activate with the old token - should still fail
        response = client.patch(
            f'/api/v1/users/activate/{old_token_id}',
            content_type='application/json',
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

        # Activate with the new token - should succeed
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
    # Get current time
    now = timezone.now()

    # Create user
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

        # Get the activation token
        User = get_user_model()
        user = User.objects.get(id=user_id)
        activation_token = ActivationToken.objects.get(user=user)

    # Try to resend while token is still valid - should fail
    with freeze_time(now + timedelta(minutes=5)):
        response = client.post(
            f'/api/v1/users/resend-activation/{activation_token.id}',
            content_type='application/json',
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.django_db
def test_resend_activation_with_already_used_token(client):
    """Test that resend fails when token has already been used"""
    # Get current time
    now = timezone.now()

    # Create user
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

        # Get the activation token
        User = get_user_model()
        user = User.objects.get(id=user_id)
        activation_token = ActivationToken.objects.get(user=user)

        # Extract token from email and activate user
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        match = re.search(r'/activate/([0-9a-fA-F-]{36})', email.body)
        token_from_email = match.group(1) if match else None

        # Activate the user
        client.patch(f'/api/v1/users/activate/{token_from_email}')

    # Move time forward so token is expired and already used
    with freeze_time(now + timedelta(minutes=16)):
        response = client.post(
            f'/api/v1/users/resend-activation/{activation_token.id}',
            content_type='application/json',
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.django_db
def test_resend_activation_with_already_active_user(client):
    """Test that resend fails when user is already activated"""
    # Get current time
    now = timezone.now()

    # Create user and immediately activate
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

        # Get the activation token
        User = get_user_model()
        user = User.objects.get(id=user_id)
        activation_token = ActivationToken.objects.get(user=user)

        # Extract token from email and activate user
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        match = re.search(r'/activate/([0-9a-fA-F-]{36})', email.body)
        token_from_email = match.group(1) if match else None

        # Activate the user
        response = client.patch(f'/api/v1/users/activate/{token_from_email}')
        assert response.status_code == HTTPStatus.OK

    # Move time forward and try to resend
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
