# api.py
from http import HTTPStatus
from ninja import NinjaAPI, Router, Schema


api = NinjaAPI()

router = Router()

api.add_router('', router)


class StatusSchema(Schema):
    status: str


@router.get('healthcheck', response=StatusSchema)
def healthcheck(request):
    return HTTPStatus.OK, {'status': 'ok'}