from django.contrib.auth.models import User
from ninja import Field, ModelSchema, Schema
from ninja.orm import create_schema


class StatusSchema(Schema):
    status: str
    db_version: str
    max_connections: int
    active_connections: int


class MigrationSchemaGet(Schema):
    pending: bool
    detail: str


class MigrationSchemaPost(Schema):
    success: bool
    detail: str


class UserSchema(ModelSchema):
    class Meta:
        model = User
        exclude = ['password', 'last_login', 'date_joined', 'user_permissions', 'groups']


UserWithGroupSchema = create_schema(
    User,
    depth=1,
    fields=['id', 'username', 'first_name', 'last_name', 'email', 'groups'],
    custom_fields=[('get_full_name', str, None)],
)


class UserCreateSchema(Schema):
    username: str = Field(..., example='newuser')
    first_name: str = Field(..., example='Firstname')
    last_name: str = Field(..., example='Lastname')
    email: str = Field(..., example='newuser@email.com')
    password: str = Field(..., example='strongpassword')


class UserPatchSchema(Schema):
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
