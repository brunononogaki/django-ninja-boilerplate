from ninja import NinjaAPI

api = NinjaAPI()

api.add_router('', 'myapi.core.api.router')
