from ninja import NinjaAPI, Redoc


api = NinjaAPI()

api.add_router('', 'myapi.core.api.router')

# Adiciona mais apps aqui
# api.add_router('', 'apps.person.api.router')