from django.contrib import admin
from django.urls import include, path

from .api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
]

api_urlpatterns = [
    path('api/v1/', api.urls),
]

urlpatterns += api_urlpatterns
