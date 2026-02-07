import uuid
from datetime import datetime
from http import HTTPStatus

from django.contrib.auth import authenticate
from django.db import connection
from loguru import logger
from ninja import Router

from .auth import create_token, verify_refresh_token
from .exceptions import ServiceError, UnauthorizedError
from .schemas import (
    LoginRequest,
    RefreshRequest,
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
@router.post('login', tags=['Auth'], response=TokenResponse)
def login(request, credentials: LoginRequest):
    user = authenticate(username=credentials.username, password=credentials.password)
    if not user:
        logger.warning(f'Failed login attempt for username: {credentials.username}')
        raise UnauthorizedError()
    logger.info(f'User {user.username} (id={user.id}) logged in')
    tokens = create_token(user)
    return 200, {'token_type': 'bearer', **tokens}


@router.post('refresh', tags=['Auth'], response=TokenResponse)
def refresh(request, credentials: RefreshRequest):
    """Refresh access token using a valid refresh token"""
    user = verify_refresh_token(credentials.refresh_token)
    if not user:
        logger.warning(f'Failed refresh attempt with invalid refresh token')
        raise UnauthorizedError(message='Invalid or expired refresh token')
    logger.info(f'User {user.username} (id={user.id}) refreshed token')
    tokens = create_token(user)
    return 200, {'token_type': 'bearer', **tokens}


@router.post('social-token', tags=['Auth'], response=TokenResponse)
def social_token(request):
    """
    Generate a JWT for the authenticated user via OAuth.
    """
    # Verifica se tem usuário autenticado (via sessão Django)
    if not request.user.is_authenticated:
        logger.warning(f'Attempt to get social token without authentication')
        raise UnauthorizedError(message='User is not authenticated')

    user = request.user
    logger.info(f'User {user.username} (id={user.id}) requested social token')

    tokens = create_token(user)
    return 200, {'token_type': 'bearer', **tokens}
