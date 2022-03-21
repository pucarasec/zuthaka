from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections

from rest_framework.authtoken.models import Token

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async

from urllib.parse import parse_qs


@database_sync_to_async
def get_user(token):
    try:
        token = Token.objects.get(key=token)
        return token.user
    except Token.DoesNotExist:
        return AnonymousUser()


class TokenAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    def __call__(self, scope):
        return TokenAuthMiddlewareInstance(scope, self)


class TokenAuthMiddlewareInstance:
    def __init__(self, scope, middleware):
        self.middleware = middleware
        self.scope = dict(scope)
        self.inner = self.middleware.inner

    async def __call__(self, receive, send):
        query = parse_qs(self.scope["query_string"])
        token_key = query.get(b"access_token")
        if token_key:
            clean_token = token_key[0].decode("utf-8")
            self.scope["user"] = await get_user(clean_token)
            close_old_connections()
        return await self.inner(self.scope, receive, send)


TokenAuthMiddlewareStack = lambda inner: TokenAuthMiddleware(AuthMiddlewareStack(inner))
