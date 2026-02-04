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
        data=json.dumps({'username': 'active_user', 'password': 'testpassword'}),
        content_type='application/json',
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
        data=json.dumps({'username': 'inactive_user', 'password': 'testpassword'}),
        content_type='application/json',
    )

    # Should return 403 Forbidden
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_login_invalid_credentials(client):
    response = client.post(
        '/api/v1/login',
        data=json.dumps({'username': config('DJANGO_ADMIN_USER'), 'password': 'wrongpassword'}),
        content_type='application/json',
    )
    data = response.json()
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert data['message'] == 'Invalid credentials.'


@pytest.mark.django_db
def test_login_missing_fields(client):
    response = client.post(
        '/api/v1/login',
        data=json.dumps({}),
        content_type='application/json',
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.django_db
def test_refresh_token_success(client):
    """Test refreshing access token before it expires"""
    # Capture the initial time as reference
    initial_time = timezone.now()

    # Step 1: Login and get tokens
    response = client.post(
        '/api/v1/login',
        data=json.dumps({'username': config('DJANGO_ADMIN_USER'), 'password': config('DJANGO_ADMIN_PASSWORD')}),
        content_type='application/json',
    )
    data = response.json()
    access_token_1 = data['access_token']
    refresh_token = data['refresh_token']
    assert response.status_code == HTTPStatus.OK

    # Step 2: Advance 14 minutes (access token expires in 15)
    with freeze_time(initial_time + timedelta(minutes=14)):
        # Step 3: Call refresh endpoint
        response = client.post(
            '/api/v1/refresh',
            data=json.dumps({'refresh_token': refresh_token}),
            content_type='application/json',
        )
        data = response.json()
        access_token_2 = data['access_token']

        # Step 4: Verify we got a new token (different from the first)
        assert response.status_code == HTTPStatus.OK
        assert 'access_token' in data
        assert access_token_1 != access_token_2  # Token deve ser diferente
        assert data['token_type'] == 'bearer'

        # Step 5: Advance more 10 minutes (total 24 minutes from start)
        # Old access_token_1 should be expired, but access_token_2 should be valid
        with freeze_time(initial_time + timedelta(minutes=24)):
            # Try to use access_token_2 (should still work)
            response = client.get(
                '/api/v1/users',
                HTTP_AUTHORIZATION=f'Bearer {access_token_2}',
            )
            # Should work because token_2 is fresh and only 10 minutes old
            assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_refresh_token_expired(client):
    """Test that expired refresh tokens are rejected"""
    # Login to get tokens
    response = client.post(
        '/api/v1/login',
        data=json.dumps({'username': config('DJANGO_ADMIN_USER'), 'password': config('DJANGO_ADMIN_PASSWORD')}),
        content_type='application/json',
    )
    data = response.json()
    refresh_token = data['refresh_token']

    # Advance 31 days (refresh token expires in 30)
    with freeze_time(timezone.now() + timedelta(days=31)):
        response = client.post(
            '/api/v1/refresh',
            data=json.dumps({'refresh_token': refresh_token}),
            content_type='application/json',
        )

        # Should fail because refresh token is expired
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert 'Invalid or expired refresh token' in response.json()['message']
