import hmac
from functools import wraps

from flask import current_app, request

from src.utils.errors import ForbiddenError

ADMIN_TOKEN_HEADER = "X-Admin-Token"


def admin_only(view):
    """Libera a rota só com ADMIN_ENDPOINTS_ENABLED=true e o header X-Admin-Token igual a ADMIN_TOKEN."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        config = current_app.config
        esperado = config.get("ADMIN_TOKEN") or ""
        recebido = request.headers.get(ADMIN_TOKEN_HEADER, "")
        if (
            not config.get("ADMIN_ENDPOINTS_ENABLED")
            or not esperado
            or not hmac.compare_digest(recebido.encode(), esperado.encode())
        ):
            raise ForbiddenError("Endpoint administrativo desabilitado ou token inválido")
        return view(*args, **kwargs)

    return wrapper
