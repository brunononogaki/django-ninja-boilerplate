# myapi/core/auth.py
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from ninja.security import APIKeyCookie

from .models import RefreshTokenDenylist

User = get_user_model()
ALGO = 'HS256'
ACCESS_LIFETIME = timedelta(minutes=15)
REFRESH_LIFETIME = timedelta(days=30)


def create_token(user):
    now = datetime.utcnow()
    access_token = jwt.encode(
        {'user_id': str(user.id), 'exp': now + ACCESS_LIFETIME, 'type': 'access'},
        settings.SECRET_KEY,
        algorithm=ALGO,
    )
    refresh_token = jwt.encode(
        {'user_id': str(user.id), 'exp': now + REFRESH_LIFETIME, 'type': 'refresh', 'jti': str(uuid4())},
        settings.SECRET_KEY,
        algorithm=ALGO,
    )
    return {'access_token': access_token, 'refresh_token': refresh_token}


def verify_refresh_token(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGO])
        if payload.get('type') != 'refresh':
            return None

        jti = payload.get('jti')
        exp = payload.get('exp')

        RefreshTokenDenylist.cleanup_expired()

        if RefreshTokenDenylist.objects.filter(jti=jti).exists():
            return None

        RefreshTokenDenylist.objects.create(
            jti=jti,
            expires_at=datetime.fromtimestamp(exp, tz=timezone.utc),
        )

        user_id = payload.get('user_id')
        return User.objects.get(id=user_id)
    except jwt.ExpiredSignatureError:
        return None
    except Exception:
        return None


def set_auth_cookies(response, tokens):
    """Seta os cookies httpOnly de autenticação na resposta."""
    secure = getattr(settings, 'COOKIE_SECURE', False)
    domain = getattr(settings, 'COOKIE_DOMAIN', None)
    response.set_cookie(
        'access_token',
        tokens['access_token'],
        max_age=int(ACCESS_LIFETIME.total_seconds()),
        httponly=True,
        secure=secure,
        samesite='Lax',
        domain=domain,
    )
    response.set_cookie(
        'refresh_token',
        tokens['refresh_token'],
        max_age=int(REFRESH_LIFETIME.total_seconds()),
        httponly=True,
        secure=secure,
        samesite='Lax',
        domain=domain,
    )
    response.set_cookie(
        'is_logged_in',
        'true',
        max_age=int(REFRESH_LIFETIME.total_seconds()),
        httponly=False,
        secure=secure,
        samesite='Lax',
        domain=domain,
    )


def clear_auth_cookies(response):
    """Remove todos os cookies de autenticação da resposta."""
    domain = getattr(settings, 'COOKIE_DOMAIN', None)
    response.delete_cookie('access_token', domain=domain, samesite='Lax')
    response.delete_cookie('refresh_token', domain=domain, samesite='Lax')
    response.delete_cookie('is_logged_in', domain=domain, samesite='Lax')


class JWTAuth(APIKeyCookie):
    param_name = 'access_token'

    def authenticate(self, request, key):  # noqa: PLR6301
        try:
            payload = jwt.decode(key, settings.SECRET_KEY, algorithms=[ALGO])
            if payload.get('type') != 'access':
                return None
            user_id = payload.get('user_id')
            return User.objects.get(id=user_id)
        except jwt.ExpiredSignatureError:
            return None
        except Exception:
            return None


class AdminAuth(JWTAuth):
    def authenticate(self, request, key):
        user = super().authenticate(request, key)
        if not user:
            return None
        if not getattr(user, 'is_staff', False):
            return None
        return user


class OwnerOrAdminAuth(JWTAuth):
    def authenticate(self, request, key):
        user = super().authenticate(request, key)
        if not user:
            return None

        target_identifier = str(request.resolver_match.kwargs.get('id', ''))

        if not target_identifier:
            return user if getattr(user, 'is_staff', False) else None

        if getattr(user, 'is_staff', False):
            return user

        if str(user.id) == target_identifier:
            return user

        return None
