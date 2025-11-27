import json
from http import HTTPStatus

import pytest


@pytest.mark.django_db
def test_create_users_success(client):
    """
    Tests the users POST endpoint.
    """
    new_user = {
        'username': 'admin',
        'first_name': 'Admin',
        'last_name': 'Admin',
        'email': 'admin@admin.com',
        'password': 'myadminpassword',
    }
    response = client.post('/api/v1/users', data=json.dumps(new_user), content_type='application/json')
    assert response.status_code == HTTPStatus.CREATED

    response = client.get('/api/v1/users')
    response_json = response.json()
    print(response_json)
    assert response.status_code == HTTPStatus.OK
    assert response_json.get('count') == 1
    assert response_json.get('items')[0].get('username') == 'admin'


@pytest.mark.django_db
def test_list_users(client):
    """
    Tests the users GET endpoint.
    """
    new_user = {
        'username': 'admin',
        'first_name': 'Admin',
        'last_name': 'Admin',
        'email': 'admin@admin.com',
        'password': 'myadminpassword',
    }
    response = client.post('/api/v1/users', data=json.dumps(new_user), content_type='application/json')
    assert response.status_code == HTTPStatus.CREATED

    response = client.get('/api/v1/users')
    response_json = response.json()
    print(response_json)
    assert response.status_code == HTTPStatus.OK
    assert response_json.get('count') == 1
    assert response_json.get('items')[0].get('username') == 'admin'


@pytest.mark.django_db
def test_create_users_duplicated_username(client):
    """
    Tests the users create endpoint.
    """
    new_user = {
        'username': 'admin',
        'first_name': 'Admin',
        'last_name': 'Admin',
        'email': 'admin@admin.com',
        'password': 'myadminpassword',
    }
    response = client.post('/api/v1/users', data=json.dumps(new_user), content_type='application/json')
    assert response.status_code == HTTPStatus.CREATED

    new_user = {
        'username': 'admin',
        'first_name': 'Admin',
        'last_name': 'Admin',
        'email': 'admin1@admin.com',
        'password': 'myadminpassword',
    }
    response = client.post('/api/v1/users', data=json.dumps(new_user), content_type='application/json')
    assert response.status_code == HTTPStatus.CONFLICT


@pytest.mark.django_db
def test_create_users_duplicated_email(client):
    """
    Tests the users create endpoint.
    """
    new_user = {
        'username': 'admin',
        'first_name': 'Admin',
        'last_name': 'Admin',
        'email': 'admin@admin.com',
        'password': 'myadminpassword',
    }
    response = client.post('/api/v1/users', data=json.dumps(new_user), content_type='application/json')
    assert response.status_code == HTTPStatus.CREATED

    new_user = {
        'username': 'admin1',
        'first_name': 'Admin',
        'last_name': 'Admin',
        'email': 'admin@admin.com',
        'password': 'myadminpassword',
    }
    response = client.post('/api/v1/users', data=json.dumps(new_user), content_type='application/json')
    assert response.status_code == HTTPStatus.CONFLICT


@pytest.mark.django_db
def test_get_user_detail(client):
    """
    Tests the users GET endpoint.
    """
    new_user = {
        'username': 'admin',
        'first_name': 'Admin',
        'last_name': 'Admin',
        'email': 'admin@admin.com',
        'password': 'myadminpassword',
    }
    response = client.post('/api/v1/users', data=json.dumps(new_user), content_type='application/json')
    response_json = response.json()
    assert response.status_code == HTTPStatus.CREATED
    user_id = response_json.get('message').get('id')

    response = client.get(f'/api/v1/users/{user_id}')
    response_json = response.json()
    assert response.status_code == HTTPStatus.OK
    assert response_json.get('id') == user_id


@pytest.mark.django_db
def test_delete_user(client):
    """
    Tests the users DELETE endpoint.
    """
    new_user = {
        'username': 'admin',
        'first_name': 'Admin',
        'last_name': 'Admin',
        'email': 'admin@admin.com',
        'password': 'myadminpassword',
    }
    response = client.post('/api/v1/users', data=json.dumps(new_user), content_type='application/json')
    response_json = response.json()
    assert response.status_code == HTTPStatus.CREATED
    user_id = response_json.get('message').get('id')

    response = client.delete(f'/api/v1/users/{user_id}')
    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.mark.django_db
def test_patch_user(client):
    """
    Tests the users PATCH endpoint.
    """
    new_user = {
        'username': 'admin',
        'first_name': 'Admin',
        'last_name': 'Admin',
        'email': 'admin@admin.com',
        'password': 'myadminpassword',
    }
    response = client.post('/api/v1/users', data=json.dumps(new_user), content_type='application/json')
    response_json = response.json()

    assert response.status_code == HTTPStatus.CREATED
    user_id = response_json.get('message').get('id')

    patch_data = {
        'first_name': 'NewName',
        'email': 'newemail@admin.com',
    }

    response = client.patch(f'/api/v1/users/{user_id}', data=json.dumps(patch_data), content_type='application/json')

    assert response.status_code == HTTPStatus.OK
    response_json = response.json()

    assert response_json['first_name'] == 'NewName'
    assert response_json['email'] == 'newemail@admin.com'
