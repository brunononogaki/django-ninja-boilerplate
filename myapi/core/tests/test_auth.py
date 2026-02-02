import json
from http import HTTPStatus

import pytest
from decouple import config
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_login_success(client):
    response = client.post(
        '/api/v1/login',
        data={'username': config('DJANGO_ADMIN_USER'), 'password': config('DJANGO_ADMIN_PASSWORD')},
    )
    data = response.json()
    assert response.status_code == HTTPStatus.OK
    assert 'access_token' in data
    assert data['token_type'] == 'bearer'
    assert 'refresh_token' in data


@pytest.mark.django_db
def test_login_active_user(client):
    """Test that active users can login"""

    # Create a new user
    user_payload = {
        'username': 'active_user',
        'first_name': 'Active',
        'last_name': 'User',
        'email': 'active@test.com',
        'password': 'testpassword',
    }
    response = client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )
    assert response.status_code == HTTPStatus.CREATED

    # Activate User
    User = get_user_model()
    user = User.objects.get(username='active_user')
    user.is_active = True
    user.save()

    # Try to login with inactive user
    response = client.post(
        '/api/v1/login',
        data={'username': 'active_user', 'password': 'testpassword'},
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
        data={'username': 'inactive_user', 'password': 'testpassword'},
    )

    # Should return 403 Forbidden
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_login_invalid_credentials(client):
    response = client.post(
        '/api/v1/login',
        data={'username': config('DJANGO_ADMIN_USER'), 'password': 'wrongpassword'},
    )
    data = response.json()
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert data['message'] == 'Invalid credentials.'


@pytest.mark.django_db
def test_login_missing_fields(client):
    response = client.post(
        '/api/v1/login',
        data={},
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
