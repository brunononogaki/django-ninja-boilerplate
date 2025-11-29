import json
from http import HTTPStatus

import pytest
from decouple import config
from django.contrib.auth import get_user_model


@pytest.fixture
def create_admin_access_token(client):
    response = client.post(
        '/api/v1/login',
        data={'username': config('DJANGO_ADMIN_USER'), 'password': config('DJANGO_ADMIN_PASSWORD')},
    )
    response_json = response.json()
    access_token = response_json['access_token']
    return access_token


@pytest.fixture
def create_non_admin_access_token(client, create_admin_access_token):
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
        HTTP_AUTHORIZATION=f'Bearer {create_admin_access_token}',
    )

    # Get the auth token for the non-admin user
    response = client.post(
        '/api/v1/login',
        data={'username': 'new_user_non_admin', 'password': 'myuserpassword'},
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
def test_get_user_detail_user_to_himself(client, create_non_admin_access_token):
    User = get_user_model()
    user = User.objects.get(username='new_user_non_admin')

    response = client.get(f'/api/v1/users/{user.id}', HTTP_AUTHORIZATION=f'Bearer {create_non_admin_access_token}')
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
def test_create_users_success(client, create_admin_access_token):
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
    response_json = response.json()

    assert response.status_code == HTTPStatus.CREATED
    assert response_json['username'] == user_payload['username']


@pytest.mark.django_db
def test_create_users_unauthorized(client, create_non_admin_access_token):
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
        HTTP_AUTHORIZATION=f'Bearer {create_non_admin_access_token}',
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


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
