"""Guards das rotas de gestão: exigem o token do /login (header `Authorization: Bearer <token>`).

Sem token, token adulterado/expirado ou usuário inexistente → 401; papel insuficiente ou
agir em nome de outro usuário → 403.
O papel vem do banco a cada requisição, nunca do token nem do corpo da requisição.
"""
from functools import wraps

from flask import g, request

from src.models import usuario_model
from src.models.tipos_usuario import TIPO_ADMIN
from src.services import token_service
from src.utils.errors import ForbiddenError, UnauthorizedError

ESQUEMA_BEARER = "bearer"


def _token_da_requisicao():
    esquema, _, token = request.headers.get("Authorization", "").partition(" ")
    return token.strip() if esquema.lower() == ESQUEMA_BEARER else ""


def _usuario_autenticado():
    token = _token_da_requisicao()
    usuario_id = token_service.ler_usuario_id(token) if token else None
    usuario = usuario_model.buscar_por_id(usuario_id) if usuario_id is not None else None
    if usuario is None:
        raise UnauthorizedError("Autenticação necessária")
    g.usuario = usuario
    return usuario


def login_required(view):
    """Exige um usuário autenticado (qualquer papel); o controller o lê de `g.usuario`."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        _usuario_autenticado()
        return view(*args, **kwargs)
    return wrapper


def exigir_dono_ou_admin(usuario_id):
    """O usuário autenticado só age em nome de si mesmo, salvo se for administrador."""
    if g.usuario["tipo"] != TIPO_ADMIN and g.usuario["id"] != usuario_id:
        raise ForbiddenError("Acesso negado")


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if _usuario_autenticado()["tipo"] != TIPO_ADMIN:
            raise ForbiddenError("Acesso restrito a administradores")
        return view(*args, **kwargs)
    return wrapper


def owner_or_admin(parametro):
    """Libera o dono do recurso (id do usuário no parâmetro da URL) ou um administrador."""
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            _usuario_autenticado()
            exigir_dono_ou_admin(kwargs[parametro])
            return view(*args, **kwargs)
        return wrapper
    return decorator
