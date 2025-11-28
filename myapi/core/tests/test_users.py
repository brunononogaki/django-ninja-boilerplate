import json
from http import HTTPStatus

import pytest


@pytest.mark.django_db
def test_list_users(client):
    response = client.get('/api/v1/users')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['count'] == 1
    assert data['items'][0]['username'] == 'admin'


@pytest.mark.django_db
def test_get_user_detail(client):
    response = client.get('/api/v1/users')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['count'] == 1
    assert data['items'][0]['username'] == 'admin'


@pytest.mark.django_db
def test_create_users_success(client):
    user_payload = {
        'username': 'admin_new',
        'first_name': 'New',
        'last_name': 'Admin',
        'email': 'admin_new@admin.com',
        'password': 'myadminpassword',
    }
    response = client.post('/api/v1/users', data=json.dumps(user_payload), content_type='application/json')
    response_json = response.json()

    assert response.status_code == HTTPStatus.CREATED
    assert response_json['username'] == user_payload['username']


@pytest.mark.django_db
def test_create_users_duplicated_username(client):
    user_payload = {
        'username': 'admin',
        'first_name': 'New',
        'last_name': 'Admin',
        'email': 'admin_new@admin.com',
        'password': 'myadminpassword',
    }
    response = client.post('/api/v1/users', data=json.dumps(user_payload), content_type='application/json')
    assert response.status_code == HTTPStatus.CONFLICT


@pytest.mark.django_db
def test_create_users_duplicated_email(client):
    user_payload = {
        'username': 'admin_new',
        'first_name': 'New',
        'last_name': 'Admin',
        'email': 'admin@admin.com',
        'password': 'myadminpassword',
    }
    response = client.post('/api/v1/users', data=json.dumps(user_payload), content_type='application/json')
    assert response.status_code == HTTPStatus.CONFLICT


@pytest.mark.django_db
def test_delete_user(client):
    user_payload = {
        'username': 'admin_new',
        'first_name': 'New',
        'last_name': 'Admin',
        'email': 'admin_new@admin.com',
        'password': 'myadminpassword',
    }
    response = client.post('/api/v1/users', data=json.dumps(user_payload), content_type='application/json')
    user_id = response.json()['id']

    response = client.delete(f'/api/v1/users/{user_id}')
    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.mark.django_db
def test_patch_user(client):
    user_payload = {
        'username': 'admin_new',
        'first_name': 'New',
        'last_name': 'Admin',
        'email': 'admin_new@admin.com',
        'password': 'myadminpassword',
    }
    response = client.post('/api/v1/users', data=json.dumps(user_payload), content_type='application/json')
    user_id = response.json()['id']

    patch_data = {
        'first_name': 'NewName',
        'email': 'newemail@admin.com',
    }

    response = client.patch(f'/api/v1/users/{user_id}', data=json.dumps(patch_data), content_type='application/json')

    response_json = response.json()
    assert response.status_code == HTTPStatus.OK
    assert response_json['first_name'] == 'NewName'
    assert response_json['email'] == 'newemail@admin.com'
