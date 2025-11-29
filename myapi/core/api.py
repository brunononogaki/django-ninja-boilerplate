import uuid
from http import HTTPStatus
from django.db import connection
from ninja import Router, Form
from ninja.responses import Response
from django.contrib.auth import get_user_model, authenticate
from ninja.pagination import paginate
from django.shortcuts import get_object_or_404


from .schemas import (
    StatusSchema,
    UserSchema,
    UserWithGroupsSchema,
    UserCreateSchema,
    UserPatchSchema,
    TokenResponse,
    ErrorSchema,
)

from .auth import create_token, JWTAuth, AdminAuth, OwnerOrAdminAuth

router = Router(tags=['Admin'])

User = get_user_model()


@router.get(
    'status',
    response=StatusSchema,
    summary='Status Check',
    description='Status check endpoint to monitor the API health.',
)
def status(request):
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
        'status': 'ok',
        'db_version': db_version,
        'max_connections': max_connections,
        'active_connections': active_connections,
    }


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
    return get_object_or_404(User, id=id)


@router.post(
    'users', response=UserWithGroupsSchema, summary='Create user', description='Create a new user', auth=AdminAuth()
)
def create_users(request, data: UserCreateSchema):
    # Pre-create validation: check username and email uniqueness
    if User.objects.filter(username=data.username).exists():
        return Response({'detail': 'Username or email already exist!'}, status=409)
    if User.objects.filter(email=data.email).exists():
        return Response({'detail': 'Username or email already exist!'}, status=409)

    try:
        user = User.objects.create_user(
            username=data.username,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            password=data.password,
        )
    except:
        return Response({'detail': 'Unable to create user'}, status=500)

    return Response(UserWithGroupsSchema.from_orm(user), status=201)


@router.delete(
    'users/{id}', summary='Delete user', response={204: None}, description='Delete an user', auth=OwnerOrAdminAuth()
)
def delete_user(request, id: uuid.UUID):
    user = get_object_or_404(User, id=id)
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
    user = get_object_or_404(User, id=id)

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(user, field, value)

    user.save()
    return Response(UserWithGroupsSchema.from_orm(user), status=200)


########
# AUTH
#######
@router.post('login', tags=['Auth'], response={200: TokenResponse, 401: ErrorSchema})
def login(request, username: str = Form(...), password: str = Form(...)):
    user = authenticate(username=username, password=password)
    if not user:
        return 401, {'detail': 'Invalid credentials'}
    tokens = create_token(user)
    return 200, {'access_token': tokens.get('access_token') or tokens.get('access'), 'token_type': 'bearer', **tokens}
