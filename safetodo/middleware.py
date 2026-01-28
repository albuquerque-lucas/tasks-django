import logging
from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from asgiref.sync import sync_to_async


@sync_to_async
def _get_user_for_token(raw_token):
    from django.contrib.auth.models import AnonymousUser
    from rest_framework_simplejwt.authentication import JWTAuthentication
    from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

    try:
        validated_token = JWTAuthentication().get_validated_token(raw_token)
        return JWTAuthentication().get_user(validated_token)
    except (InvalidToken, TokenError):
        return None


class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner
        self.logger = logging.getLogger(__name__)

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        query_params = parse_qs(scope.get('query_string', b'').decode())
        token = query_params.get('token', [None])[0]
        scope['jwt_invalid'] = False
        scope['jwt_invalid_reason'] = None
        if token:
            if token.startswith('Bearer '):
                scope['jwt_invalid'] = True
                scope['jwt_invalid_reason'] = 'bearer_prefix_not_allowed'
                self.logger.info('WS token auth invalid: bearer prefix not allowed')
                return await self.inner(scope, receive, send)
            user = await _get_user_for_token(token)
            if user:
                scope['user'] = user
                self.logger.info('WS token auth ok: user=%s', getattr(user, 'id', None))
            else:
                from django.contrib.auth.models import AnonymousUser

                scope['user'] = AnonymousUser()
                scope['jwt_invalid'] = True
                scope['jwt_invalid_reason'] = 'invalid_or_expired'
                self.logger.info('WS token auth invalid')
        return await self.inner(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(AuthMiddlewareStack(inner))
