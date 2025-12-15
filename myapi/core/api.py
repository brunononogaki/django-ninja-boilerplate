import uuid
from datetime import datetime
from http import HTTPStatus

from django.contrib.auth import authenticate, get_user_model
from django.db import connection
from loguru import logger
from ninja import Form, Router
from ninja.pagination import paginate
from ninja.responses import Response

from .auth import AdminAuth, OwnerOrAdminAuth, create_token
from .exceptions import ConflictError, NotFoundError, ServiceError, UnauthorizedError
from .schemas import (
    ErrorSchema,
    StatusSchema,
    TokenResponse,
    UserCreateSchema,
    UserPatchSchema,
    UserWithGroupsSchema,
)

router = Router(tags=['Admin'])

User = get_user_model()


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
# Users
##############
@router.get(
    'users', response=list[UserWithGroupsSchema], summary='List users', description='List users', auth=AdminAuth()
)
@paginate
def list_users(request):
    return User.objects.all()


@router.get(
    'users/{id}',
    response=UserWithGroupsSchema,
    summary='Get user detail',
    description='Retrieve user details by ID',
    auth=OwnerOrAdminAuth(),
)
def get_user_detail(request, id: uuid.UUID):
    try:
        user = User.objects.get(id=id)
    except User.DoesNotExist:
        logger.warning(f'Attempt to retrieve non-existent user: {id}')
        raise NotFoundError('User not found')
    logger.info(f'User {user.username} (id={id}) retrieved by {request.auth}')
    return user


@router.post(
    'users', response=UserWithGroupsSchema, summary='Create user', description='Create a new user', auth=AdminAuth()
)
def create_users(request, data: UserCreateSchema):
    # Pre-create validation: check username and email uniqueness
    if User.objects.filter(username=data.username).exists():
        logger.warning(f'Attempt to create user with existing username: {data.username}')
        raise ConflictError('Username already exists')
    if User.objects.filter(email=data.email).exists():
        logger.warning(f'Attempt to create user with existing email: {data.email}')
        raise ConflictError('Email already exists')

    user = User.objects.create_user(
        username=data.username,
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        password=data.password,
    )

    logger.info(f'User {user.username} (id={user.id}) created by {request.auth}')
    return Response(UserWithGroupsSchema.from_orm(user), status=201)


@router.delete(
    'users/{id}', summary='Delete user', response={204: None}, description='Delete an user', auth=OwnerOrAdminAuth()
)
def delete_user(request, id: uuid.UUID):
    # user = get_object_or_404(User, id=id)
    try:
        user = User.objects.get(id=id)
    except User.DoesNotExist:
        logger.warning(f'Attempt to delete non-existent user: {id}')
        raise NotFoundError('User not found')

    logger.info(f'User {user.username} (id={id}) deleted by {request.auth}')
    user.delete()
    return Response(None, status=204)


@router.patch(
    'users/{id}',
    response=UserWithGroupsSchema,
    summary='Update user partially',
    description='Update only specified user fields',
    auth=OwnerOrAdminAuth(),
)
def patch_user(request, id: uuid.UUID, payload: UserPatchSchema):
    try:
        user = User.objects.get(id=id)
    except User.DoesNotExist:
        logger.warning(f'Attempt to update non-existent user: {id}')
        raise NotFoundError('User not found')

    updated_fields = payload.dict(exclude_unset=True)
    for field, value in updated_fields.items():
        setattr(user, field, value)

    user.save()
    logger.info(f'User {user.username} (id={id}) updated by {request.auth} - fields: {list(updated_fields.keys())}')
    return Response(UserWithGroupsSchema.from_orm(user), status=200)


########
# AUTH
#######
@router.post('login', tags=['Auth'], response={200: TokenResponse, 401: ErrorSchema})
def login(request, username: str = Form(...), password: str = Form(...)):
    user = authenticate(username=username, password=password)
    if not user:
        logger.warning(f'Failed login attempt for username: {username}')
        raise UnauthorizedError()
    logger.info(f'User {user.username} (id={user.id}) logged in')
    tokens = create_token(user)
    return 200, {'access_token': tokens.get('access_token') or tokens.get('access'), 'token_type': 'bearer', **tokens}
