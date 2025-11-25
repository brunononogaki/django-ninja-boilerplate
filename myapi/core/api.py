from http import HTTPStatus

from django.db import connection
from ninja import Router

from .schemas import (  # noqa F401
    StatusSchema,
)

router = Router(tags=['Core'])


@router.get(
    'status',
    response=StatusSchema,
    tags=['Status'],
    summary='Status',
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


# @router.get('users', response=list[UserWithGroupSchema])
# def list_users(request):
#     return User.objects.all()


# @router.get('tasks', response=list[TaskSchema], tags=['Tasks'])
# @paginate
# def list_tasks(request, filters: TaskFilterSchema = Query(...)):
#     tasks = Task.objects.all()
#     return filters.filter(tasks)
