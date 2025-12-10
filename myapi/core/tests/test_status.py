from http import HTTPStatus

import pytest


@pytest.mark.django_db
def test_status(client):
    """
    Tests the status endpoint.
    """
    response = client.get('/api/v1/status')
    response_json = response.json()

    assert response.status_code == HTTPStatus.OK
    assert 'updated_at' in response_json
    assert 'db_version' in response_json
    assert 'max_connections' in response_json
    assert 'active_connections' in response_json
    assert 'PostgreSQL 17' in response_json.get('db_version')
    assert int(response_json.get('max_connections'))
    assert int(response_json.get('active_connections'))
