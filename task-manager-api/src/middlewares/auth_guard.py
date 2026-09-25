"""Guards das rotas de gestão: exigem o token assinado de POST /login e checam o papel no banco.

- sem token, token adulterado ou expirado → 401;
- token válido sem permissão → 403;
- com permissão → a view roda sem alteração.

O usuário autenticado fica em `flask.g.current_user` para os controllers que decidem por dono.
"""
from functools import wraps

from flask import g, request

from src.utils.errors import ForbiddenError

AUTHORIZATION_HEADER = 'Authorization'
BEARER_SCHEME = 'bearer'
ACCESS_DENIED_MESSAGE = 'Acesso negado'


def _bearer_token() -> str:
    scheme, _, token = request.headers.get(AUTHORIZATION_HEADER, '').partition(' ')
    return token.strip() if scheme.lower() == BEARER_SCHEME else ''


def current_user():
    """Usuário autenticado pelo guard da rota atual."""
    return g.current_user


def ensure_can_act_for(user_id) -> None:
    """403 quando quem chama não é o usuário `user_id` nem admin (dados sem dono são compartilhados)."""
    if not current_user().can_act_for(user_id):
        raise ForbiddenError(ACCESS_DENIED_MESSAGE)


class AuthGuard:
    def __init__(self, auth_service):
        self._auth = auth_service

    def _authenticate(self):
        g.current_user = self._auth.user_from_token(_bearer_token())
        return g.current_user

    def authenticated(self, view):
        """Qualquer usuário autenticado; a regra de dono fica no controller."""
        @wraps(view)
        def wrapper(*args, **kwargs):
            self._authenticate()
            return view(*args, **kwargs)
        return wrapper

    def admin_required(self, view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not self._authenticate().is_admin:
                raise ForbiddenError(ACCESS_DENIED_MESSAGE)
            return view(*args, **kwargs)
        return wrapper

    def owner_or_admin(self, param: str):
        """O próprio usuário identificado pelo parâmetro de rota `param`, ou um admin."""
        def decorator(view):
            @wraps(view)
            def wrapper(*args, **kwargs):
                self._authenticate()
                ensure_can_act_for(kwargs[param])
                return view(*args, **kwargs)
            return wrapper
        return decorator
