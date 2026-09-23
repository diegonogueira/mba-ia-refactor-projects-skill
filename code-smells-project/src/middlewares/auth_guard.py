"""Guards das rotas com dados de terceiros ou destrutivas: fechadas por padrão (403).

O acesso exige o token devolvido pelo /login no header `Authorization: Bearer <token>`.
"""
from functools import wraps

from flask import request

from src.models.usuario_model import TIPO_ADMIN
from src.services import token_service
from src.utils.errors import ForbiddenError

BEARER_PREFIX = "Bearer "
ADMIN_REQUIRED_MESSAGE = "Acesso restrito a administradores"
OWNER_REQUIRED_MESSAGE = "Acesso restrito ao próprio usuário ou a administradores"


def _current_user():
    header = request.headers.get("Authorization", "")
    if not header.startswith(BEARER_PREFIX):
        return None
    return token_service.usuario_do_token(header[len(BEARER_PREFIX):].strip())


def _is_admin(user):
    return user is not None and user["tipo"] == TIPO_ADMIN


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not _is_admin(_current_user()):
            raise ForbiddenError(ADMIN_REQUIRED_MESSAGE)
        return view(*args, **kwargs)
    return wrapper


def owner_or_admin(user_id_param):
    """Libera quando o usuário do token é o dono do recurso (`user_id_param` da URL) ou um admin."""
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = _current_user()
            if user is None or (user["id"] != kwargs[user_id_param] and not _is_admin(user)):
                raise ForbiddenError(OWNER_REQUIRED_MESSAGE)
            return view(*args, **kwargs)
        return wrapper
    return decorator
