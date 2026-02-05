import uuid

from django.contrib.auth import get_user_model
from loguru import logger
from ninja import Router
from ninja.pagination import paginate
from ninja.responses import Response

from ..core.auth import AdminAuth, JWTAuth, OwnerOrAdminAuth
from ..core.exceptions import ConflictError, NotFoundError, ServiceError, ValidationError
from .schemas import (
    UserCreateSchema,
    UserPatchSchema,
    UserWithGroupsSchema,
)
from .models import ActivationToken
from .services import send_activation_email, verify_activation_token

router = Router(tags=['Users'])

User = get_user_model()


##############
# Me (Current User)
##############
@router.get(
    'me',
    response=UserWithGroupsSchema,
    summary='Get current user',
    description='Get the current authenticated user information',
    auth=JWTAuth(),
)
def get_current_user(request):
    logger.info(f'User {request.auth.username} retrieved their profile')
    return request.auth


##############
# Users
##############
@router.get(
    'users',
    response=list[UserWithGroupsSchema],
    summary='List users',
    description='List users or filter by id/username',
    auth=AdminAuth(),
)
@paginate
def list_users(request, id: uuid.UUID = None, username: str = None):
    queryset = User.objects.all()

    if id:
        try:
            user = User.objects.get(id=id)
            logger.info(f'User retrieved by id={id} by {request.auth}')
            return [user]
        except User.DoesNotExist:
            logger.warning(f'Attempt to retrieve non-existent user: id={id}')
            raise NotFoundError('User not found')

    if username:
        try:
            user = User.objects.get(username=username)
            logger.info(f'User retrieved by username={username} by {request.auth}')
            return [user]
        except User.DoesNotExist:
            logger.warning(f'Attempt to retrieve non-existent user: username={username}')
            raise NotFoundError('User not found')

    logger.info(f'All users retrieved by {request.auth}')
    return queryset


@router.get(
    'users/{id}',
    response=UserWithGroupsSchema,
    summary='Get user detail',
    description='Retrieve user details by ID',
    auth=OwnerOrAdminAuth(),
)
def get_user_detail_by_id(request, id: uuid.UUID):
    try:
        user = User.objects.get(id=id)
    except User.DoesNotExist:
        logger.warning(f'Attempt to retrieve non-existent user: {id}')
        raise NotFoundError('User not found')
    logger.info(f'User {user.username} (id={id}) retrieved by {request.auth}')
    return user


@router.get(
    'users/username/{username}',
    response=UserWithGroupsSchema,
    summary='Get user detail',
    description='Retrieve user details by Username',
    auth=OwnerOrAdminAuth(),
)
def get_user_detail_by_username(request, username: str):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        logger.warning(f'Attempt to retrieve non-existent user: {username}')
        raise NotFoundError('User not found')
    logger.info(f'User {user.username} retrieved by {request.auth}')
    return user


@router.post('users', response=UserWithGroupsSchema, summary='Create user', description='Create a new user', auth=None)
def create_users(request, data: UserCreateSchema):
    # Pre-create validation: check username and email uniqueness
    if User.objects.filter(username=data.username).exists():
        logger.warning(f'Attempt to create user with existing username: {data.username}')
        raise ConflictError('Username already exists')
    if User.objects.filter(email=data.email).exists():
        logger.warning(f'Attempt to create user with existing email: {data.email}')
        raise ConflictError('Email already exists')

    try:
        user = User.objects.create_user(
            username=data.username,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            password=data.password,
            is_active=False,
        )
    except Exception as e:
        logger.error(f'Failed to create user: {e}')
        raise ServiceError('An unknow Service error ocurred when creating an user.')

    # Send activation email
    try:
        send_activation_email(user)
        logger.info(f'Activation email sent to {user.email}')
    except Exception as e:
        logger.error(f'Failed to send activation email to {user.email}: {e}')

    logger.info(f'User {user.username} (id={user.id}) created')
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

    try:
        logger.info(f'User {user.username} (id={id}) deleted by {request.auth}')
        user.delete()
        return Response(None, status=204)
    except Exception as e:
        logger.error(f'Failed to delete user: {e}')
        raise ServiceError('An unknow Service error ocurred when deleting an user.')


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

    # Create a dict based on the schema UserPatchSchema, but removing fields that were not in the payload
    updated_fields = payload.dict(exclude_unset=True)
    for field, value in updated_fields.items():
        setattr(user, field, value)

    try:
        user.save()
        logger.info(
            f'User {user.username} (id={id}) updated by {request.auth} - fields: {list(updated_fields.keys())}'
        )
        return Response(UserWithGroupsSchema.from_orm(user), status=200)
    except Exception as e:
        logger.error(f'Failed to update user: {e}')
        raise ServiceError('An unknow Service error ocurred when updating an user.')


@router.patch(
    'users/activate/{token_id}',
    response=UserWithGroupsSchema,
    summary='Activate user account',
    description='Activate user account using activation token',
    auth=None,
)
def activate_user(request, token_id: uuid.UUID):
    user = verify_activation_token(str(token_id))

    if user is None:
        logger.warning(f'Attempt to activate with invalid token: token_id={token_id}')
        raise ValidationError('Invalid activation token.')

    logger.info(f'User {user.username} activated')
    return Response(UserWithGroupsSchema.from_orm(user), status=200)


@router.post(
    'users/resend-activation/{token_id}',
    response=UserWithGroupsSchema,
    summary='Generate new activation token',
    description='Generate new activation token and send via e-mail',
    auth=None,
)
def resend_activation(request, token_id: uuid.UUID):
    user = verify_activation_token(str(token_id), is_resend=True)

    # Send new activation email (which creates a new token)
    try:
        send_activation_email(user)
        logger.info(f'New activation email sent to {user.email} (old token: {token_id})')
    except Exception as e:
        logger.error(f'Failed to send activation email to {user.email}: {e}')
        raise ServiceError('Failed to send activation email. Please try again later')

    logger.info(f'User {user.username} (id={user.id}) requested token resend')
    return Response(UserWithGroupsSchema.from_orm(user), status=200)
