# myapi/core/auth.py
from datetime import datetime, timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from ninja.security import HttpBearer

User = get_user_model()
ALGO = 'HS256'
ACCESS_LIFETIME = timedelta(minutes=15)
REFRESH_LIFETIME = timedelta(days=7)


def create_token(user):
    now = datetime.utcnow()
    access_token = jwt.encode(
        {'user_id': str(user.id), 'exp': now + ACCESS_LIFETIME, 'type': 'access'},
        settings.SECRET_KEY,
        algorithm=ALGO,
    )
    refresh_token = jwt.encode(
        {'user_id': str(user.id), 'exp': now + REFRESH_LIFETIME, 'type': 'refresh'},
        settings.SECRET_KEY,
        algorithm=ALGO,
    )
    return {'access_token': access_token, 'refresh_token': refresh_token}


class JWTAuth(HttpBearer):
    @staticmethod
    def authenticate(request, token):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGO])
            if payload.get('type') != 'access':
                return None
            user_id = payload.get('user_id')
            return User.objects.get(id=user_id)
        except jwt.ExpiredSignatureError:
            return None
        except Exception:
            return None


class AdminAuth(JWTAuth):
    def authenticate(self, request, token):
        user = super().authenticate(request, token)
        if not user:
            return None
        if not getattr(user, 'is_staff', False):
            return None
        return user


class OwnerOrAdminAuth(JWTAuth):
    def authenticate(self, request, token):
        user = super().authenticate(request, token)
        if not user:
            return None

        target_identifier = None
        try:
            # Pega o ID ou username do último segmento do path
            target_identifier = str(request.path).split('/')[-1]
        except Exception:
            target_identifier = None

        # Se não há target_identifier, só admins tem acesso
        if not target_identifier:
            return user if getattr(user, 'is_staff', False) else None

        # Verifica se é admin
        if getattr(user, 'is_staff', False):
            return user

        # Para não-admins, verifica se é o próprio usuário (por ID ou username)
        if str(user.id) == str(target_identifier) or user.username == target_identifier:
            return user

        return None
