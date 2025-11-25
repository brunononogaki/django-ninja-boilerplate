from http import HTTPStatus

from django.db import connection
from ninja import Router

from .schemas import (  # noqa F401
    StatusSchema,
    TaskFilterSchema,
    TaskSchema,
    UserSchema,
    UserSimpleSchema,
    UserWithGroupSchema,
)

router = Router(tags=['Core'])


@router.get(
    'healthcheck',
    response=StatusSchema,
    tags=['Health Check'],
    summary='Health Check',
    description='Verificação de status que permite monitorar a saúde da API.',
)
def healthcheck(request):
    with connection.cursor() as cursor:
        # Versão do banco
        cursor.execute('SELECT version()')
        db_version = cursor.fetchone()[0]

        # Número máximo de conexões
        cursor.execute('SHOW max_connections')
        max_connections = cursor.fetchone()[0]

        # Conexões ativas
        cursor.execute('SELECT count(*) FROM pg_stat_activity')
        active_connections = cursor.fetchone()[0]

    return HTTPStatus.OK, {
        'status': 'ok',
        'db_version': db_version,
        'max_connections': max_connections,
        'active_connections': active_connections,
    }


# @router.get('users', response=list[UserWithGroupSchema])
# def list_users(request):
#     return User.objects.all()


# @router.get('tasks', response=list[TaskSchema], tags=['Tasks'])
# @paginate
# def list_tasks(request, filters: TaskFilterSchema = Query(...)):
#     tasks = Task.objects.all()
#     return filters.filter(tasks)
