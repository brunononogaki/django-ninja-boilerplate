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
    assert response.status_code == HTTPStatus.OK
    assert 'access_token' in response.cookies
    assert 'refresh_token' in response.cookies
    assert 'is_logged_in' in response.cookies
    assert response.cookies['access_token']['httponly']
    assert response.cookies['refresh_token']['httponly']
    assert not response.cookies['is_logged_in']['httponly']


@pytest.mark.django_db
def test_login_active_user(client):
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

    user = User.objects.get(username='active_user')
    user.is_active = True
    user.save()

    response = client.post(
        '/api/v1/login',
        data=json.dumps({'username': 'active_user', 'password': 'testpassword'}),
        content_type='application/json',
    )
    assert response.status_code == HTTPStatus.OK
    assert 'access_token' in response.cookies
    assert 'refresh_token' in response.cookies


@pytest.mark.django_db
def test_login_inactive_user(client):
    user_payload = {
        'username': 'inactive_user',
        'first_name': 'Inactive',
        'last_name': 'User',
        'email': 'inactive@test.com',
        'password': 'testpassword',
    }
    client.post(
        '/api/v1/users',
        data=json.dumps(user_payload),
        content_type='application/json',
    )

    response = client.post(
        '/api/v1/login',
        data=json.dumps({'username': 'inactive_user', 'password': 'testpassword'}),
        content_type='application/json',
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert 'access_token' not in response.cookies


@pytest.mark.django_db
def test_login_invalid_credentials(client):
    response = client.post(
        '/api/v1/login',
        data=json.dumps({'username': config('DJANGO_ADMIN_USER'), 'password': 'wrongpassword'}),
        content_type='application/json',
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['message'] == 'Invalid credentials.'
    assert 'access_token' not in response.cookies


@pytest.mark.django_db
def test_login_missing_fields(client):
    response = client.post(
        '/api/v1/login',
        data=json.dumps({}),
        content_type='application/json',
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.django_db
def test_logout_clears_cookies(client):
    client.post(
        '/api/v1/login',
        data=json.dumps({'username': config('DJANGO_ADMIN_USER'), 'password': config('DJANGO_ADMIN_PASSWORD')}),
        content_type='application/json',
    )
    response = client.post('/api/v1/logout')
    assert response.status_code == HTTPStatus.OK
    assert response.cookies['access_token']['max-age'] == 0
    assert response.cookies['refresh_token']['max-age'] == 0
    assert response.cookies['is_logged_in']['max-age'] == 0


@pytest.mark.django_db
def test_refresh_token_success(client):
    initial_time = timezone.now()

    client.post(
        '/api/v1/login',
        data=json.dumps({'username': config('DJANGO_ADMIN_USER'), 'password': config('DJANGO_ADMIN_PASSWORD')}),
        content_type='application/json',
    )

    with freeze_time(initial_time + timedelta(minutes=14)):
        # O cliente de testes guarda os cookies do login e os envia automaticamente
        response = client.post('/api/v1/refresh')
        assert response.status_code == HTTPStatus.OK
        assert 'access_token' in response.cookies

        with freeze_time(initial_time + timedelta(minutes=24)):
            # Acessa endpoint protegido com o novo cookie
            response = client.get('/api/v1/me')
            assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_refresh_token_expired(client):
    client.post(
        '/api/v1/login',
        data=json.dumps({'username': config('DJANGO_ADMIN_USER'), 'password': config('DJANGO_ADMIN_PASSWORD')}),
        content_type='application/json',
    )

    with freeze_time(timezone.now() + timedelta(days=31)):
        response = client.post('/api/v1/refresh')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert 'Invalid or expired refresh token' in response.json()['message']


@pytest.mark.django_db
def test_refresh_token_without_cookie(client):
    response = client.post('/api/v1/refresh')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_protected_endpoint_with_cookie(client):
    client.post(
        '/api/v1/login',
        data=json.dumps({'username': config('DJANGO_ADMIN_USER'), 'password': config('DJANGO_ADMIN_PASSWORD')}),
        content_type='application/json',
    )
    response = client.get('/api/v1/me')
    assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_protected_endpoint_without_cookie(client):
    response = client.get('/api/v1/me')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_social_token_success(client):
    User.objects.create_user(username='google_user', email='google@example.com', password='testpass123')
    client.login(username='google_user', password='testpass123')

    response = client.post('/api/v1/social-token')

    assert response.status_code == HTTPStatus.OK
    assert 'access_token' in response.cookies
    assert 'refresh_token' in response.cookies
    assert 'is_logged_in' in response.cookies


@pytest.mark.django_db
def test_social_token_not_authenticated(client):
    response = client.post('/api/v1/social-token')
    assert response.status_code == HTTPStatus.UNAUTHORIZED
