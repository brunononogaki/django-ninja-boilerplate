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
def test_login_invalid_credentials(client):
    response = client.post(
        '/api/v1/login',
        data={'username': config('DJANGO_ADMIN_USER'), 'password': 'wrongpassword'},
    )
    data = response.json()
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert data['detail'] == 'Invalid credentials'


@pytest.mark.django_db
def test_login_missing_fields(client):
    response = client.post(
        '/api/v1/login',
        data={},
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
