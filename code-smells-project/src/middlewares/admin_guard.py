"""Guard dos endpoints administrativos: desabilitados por padrão e protegidos por token quando habilitados."""
import hmac
from functools import wraps

from flask import current_app, request

from src.utils.errors import ForbiddenError

ADMIN_TOKEN_HEADER = "X-Admin-Token"


def admin_only(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        config = current_app.config
        expected_token = config["ADMIN_TOKEN"] or ""
        received_token = request.headers.get(ADMIN_TOKEN_HEADER, "")
        if not config["ADMIN_ENDPOINTS_ENABLED"] or not expected_token \
                or not hmac.compare_digest(received_token.encode(), expected_token.encode()):
            raise ForbiddenError("Endpoints administrativos desabilitados ou token inválido")
        return view(*args, **kwargs)
    return wrapper
