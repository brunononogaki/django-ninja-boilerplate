# api.py
from http import HTTPStatus
from ninja import NinjaAPI, Router, Schema


api = NinjaAPI()

router = Router()

api.add_router('', router)


class StatusSchema(Schema):
    status: str


@router.get(
    'healthcheck',
    response=StatusSchema,
    tags=['Health Check'],
    summary='Health Check Summary',
    description='Verificação de status que permite monitorar a saúde da API.'
)
def healthcheck(request):
    return HTTPStatus.OK, {'status': 'ok'}