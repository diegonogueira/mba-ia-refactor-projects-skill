"""Guard dos endpoints administrativos: desabilitados por padrão e protegidos por token quando habilitados."""
import hmac
from functools import wraps

from flask import current_app, request

from src.utils.errors import ForbiddenError

HEADER_TOKEN = "X-Admin-Token"


def admin_only(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        config = current_app.config
        token_esperado = config["ADMIN_TOKEN"] or ""
        token_recebido = request.headers.get(HEADER_TOKEN, "")
        if not config["ADMIN_ENDPOINTS_ENABLED"] or not token_esperado \
                or not hmac.compare_digest(token_recebido.encode(), token_esperado.encode()):
            raise ForbiddenError("Endpoints administrativos desabilitados ou token inválido")
        return view(*args, **kwargs)
    return wrapper
