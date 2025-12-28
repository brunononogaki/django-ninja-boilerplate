from datetime import datetime
from http import HTTPStatus

from django.contrib.auth import authenticate
from django.db import connection
from loguru import logger
from ninja import Form, Router

from .auth import create_token
from .exceptions import ServiceError, UnauthorizedError
from .schemas import (
    ErrorSchema,
    StatusSchema,
    TokenResponse,
)

router = Router(tags=['Admin'])


##############
# STATUS
##############
@router.get(
    'status',
    response=StatusSchema,
    summary='Status Check',
    description='Status check endpoint to monitor the API health.',
)
def status(request):
    try:
        with connection.cursor() as cursor:
            # Database version
            cursor.execute('SELECT version()')
            db_version = cursor.fetchone()[0]

            # Maximum number of connections
            cursor.execute('SHOW max_connections')
            max_connections = int(cursor.fetchone()[0])

            # Active connections
            cursor.execute('SELECT count(*) FROM pg_stat_activity')
            active_connections = int(cursor.fetchone()[0])

        return HTTPStatus.OK, {
            'updated_at': str(datetime.now()),
            'db_version': db_version,
            'max_connections': max_connections,
            'active_connections': active_connections,
        }
    except Exception as e:
        logger.error(f'Database Error: {e}')
        raise ServiceError(message='Ocorreu um erro ao acessar o banco de dados ou executar uma query.')


##############
# AUTH
##############
@router.post('login', tags=['Auth'], response={200: TokenResponse, 401: ErrorSchema})
def login(request, username: str = Form(...), password: str = Form(...)):
    user = authenticate(username=username, password=password)
    if not user:
        logger.warning(f'Failed login attempt for username: {username}')
        raise UnauthorizedError()
    logger.info(f'User {user.username} (id={user.id}) logged in')
    tokens = create_token(user)
    return 200, {'access_token': tokens.get('access_token') or tokens.get('access'), 'token_type': 'bearer', **tokens}
