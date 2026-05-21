from datetime import datetime
from http import HTTPStatus

from django.contrib.auth import authenticate
from django.db import connection
from django.http import HttpResponse
from loguru import logger
from ninja import Router

from .auth import clear_auth_cookies, create_token, set_auth_cookies, verify_refresh_token
from .exceptions import ServiceError, UnauthorizedError
from .schemas import LoginRequest, MessageSchema, StatusSchema

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
            cursor.execute('SELECT version()')
            db_version = cursor.fetchone()[0]

            cursor.execute('SHOW max_connections')
            max_connections = int(cursor.fetchone()[0])

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
@router.post('login', tags=['Auth'], response={200: MessageSchema})
def login(request, response: HttpResponse, credentials: LoginRequest):
    user = authenticate(username=credentials.username, password=credentials.password)
    if not user:
        logger.warning(f'Failed login attempt for username: {credentials.username}')
        raise UnauthorizedError()
    logger.info(f'User {user.username} (id={user.id}) logged in')
    tokens = create_token(user)
    set_auth_cookies(response, tokens)
    return 200, {'message': 'Login realizado com sucesso'}


@router.post('refresh', tags=['Auth'], response={200: MessageSchema})
def refresh(request, response: HttpResponse):
    refresh_token = request.COOKIES.get('refresh_token')
    if not refresh_token:
        raise UnauthorizedError(message='Refresh token não encontrado')
    user = verify_refresh_token(refresh_token)
    if not user:
        logger.warning('Failed refresh attempt with invalid refresh token')
        raise UnauthorizedError(message='Invalid or expired refresh token')
    logger.info(f'User {user.username} (id={user.id}) refreshed token')
    tokens = create_token(user)
    set_auth_cookies(response, tokens)
    return 200, {'message': 'Token renovado com sucesso'}


@router.post('logout', tags=['Auth'], response={200: MessageSchema})
def logout(request, response: HttpResponse):
    clear_auth_cookies(response)
    logger.info('User logged out')
    return 200, {'message': 'Logout realizado com sucesso'}


@router.post('social-token', tags=['Auth'], response={200: MessageSchema})
def social_token(request, response: HttpResponse):
    """Generate a JWT for the authenticated user via OAuth."""
    if not request.user.is_authenticated:
        logger.warning('Attempt to get social token without authentication')
        raise UnauthorizedError(message='User is not authenticated')
    user = request.user
    logger.info(f'User {user.username} (id={user.id}) requested social token')
    tokens = create_token(user)
    set_auth_cookies(response, tokens)
    return 200, {'message': 'Token gerado com sucesso'}
