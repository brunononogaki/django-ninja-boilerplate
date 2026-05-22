from django_ratelimit.core import is_ratelimited
from ninja.errors import HttpError


def check_rate_limit(request, group: str, rate: str = '5/m') -> None:
    limited = is_ratelimited(request, group=group, key='ip', rate=rate, increment=True)
    if limited:
        raise HttpError(429, 'Muitas tentativas. Tente novamente mais tarde.')
