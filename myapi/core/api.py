from http import HTTPStatus

from django.contrib.auth.models import User
from django.db import IntegrityError, connection
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import paginate
from ninja.responses import Response

from .schemas import (
    StatusSchema,
    UserCreateSchema,
    UserPatchSchema,
    UserWithGroupSchema,
)

router = Router(tags=['Admin'])


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


@router.get(
    'users',
    response=list[UserWithGroupSchema],
    summary='List users',
    description='List users',
)
@paginate
def list_users(request):
    return User.objects.all()


@router.get(
    'users/{id}',
    response=UserWithGroupSchema,
    summary='Get user detail',
    description='Retrieve user details by ID',
)
def get_user_detail(request, id: int):
    return get_object_or_404(User, id=id)


@router.post(
    'users',
    response=UserWithGroupSchema,
    summary='Create user',
    description='Create a new user',
)
def create_users(request, data: UserCreateSchema):
    # Pre-create validation: check username and email uniqueness
    if User.objects.filter(username=data.username).exists():
        return Response({'success': False, 'message': 'username already exists'}, status=409)
    if User.objects.filter(email=data.email).exists():
        return Response({'success': False, 'message': 'email already exists'}, status=409)

    try:
        user = User.objects.create_user(
            username=data.username,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            password=data.password,
        )
    except IntegrityError:
        # In case of race condition or DB constraint, return conflict
        return Response({'success': False, 'message': 'user could not be created (conflict)'}, status=409)

    payload = {'success': True, 'message': UserWithGroupSchema.from_orm(user)}
    return Response(payload, status=201)


@router.delete(
    'users/{id}',
    summary='Delete user',
    response={204: None},
    description='Delete an user',
)
def delete_user(request, id: int):
    user = get_object_or_404(User, id=id)
    user.delete()
    return 204, None


@router.patch(
    'users/{id}',
    response=UserWithGroupSchema,
    summary='Update user partially',
    description='Update only specified user fields',
)
def patch_user(request, id: int, payload: UserPatchSchema):
    user = get_object_or_404(User, id=id)

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(user, field, value)

    user.save()
    return user
