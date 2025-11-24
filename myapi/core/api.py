from http import HTTPStatus
from ninja import Router

from .schemas import StatusSchema


router = Router(tags=['Core'])


@router.get(
    'healthcheck',
    response=StatusSchema,
    tags=['Health Check'],
    summary='Health Check Summary',
    description='Verificação de status que permite monitorar a saúde da API.'
)
def healthcheck(request):
    return HTTPStatus.OK, {'status': 'ok'}