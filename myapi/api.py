from ninja import NinjaAPI

from myapi.core.exceptions import APIException

api = NinjaAPI()


@api.exception_handler(APIException)
def handle_api_exception(request, exc):
    return api.create_response(
        request,
        {
            'name': exc.name,
            'message': exc.message,
            'status_code': exc.status_code,
        },
        status=exc.status_code,
    )


api.add_router('', 'myapi.core.api.router')
api.add_router('', 'myapi.users.api.router')
