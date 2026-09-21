"""Guard dos endpoints destrutivos de administração — fechado por padrão.

Enquanto a API não exige autenticação, um endpoint que apaga a conta de qualquer pessoa
(e, em cascata, as tasks dela) não pode ficar aberto. O guard só deixa passar quando o
ambiente traz `ADMIN_ENDPOINTS_ENABLED` **e** `ADMIN_TOKEN`; sem configuração, recusa.
"""
import hmac
from functools import wraps

from flask import current_app, request

from src.utils.errors import ForbiddenError

ADMIN_TOKEN_HEADER = 'X-Admin-Token'
ADMIN_DISABLED_MESSAGE = 'Endpoint administrativo desabilitado'
ADMIN_TOKEN_INVALID_MESSAGE = 'Token administrativo inválido'


def _tokens_match(sent: str, expected: str) -> bool:
    """Comparação em tempo constante, tolerante a bytes não-ASCII no header."""
    return hmac.compare_digest(sent.encode('utf-8'), expected.encode('utf-8'))


def admin_only(view):
    """Recusa com 403 a menos que a flag e o token administrativos estejam configurados."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        config = current_app.config
        if not config.get('ADMIN_ENDPOINTS_ENABLED') or not config.get('ADMIN_TOKEN'):
            raise ForbiddenError(ADMIN_DISABLED_MESSAGE)
        if not _tokens_match(request.headers.get(ADMIN_TOKEN_HEADER, ''), config['ADMIN_TOKEN']):
            raise ForbiddenError(ADMIN_TOKEN_INVALID_MESSAGE)
        return view(*args, **kwargs)

    return wrapper
