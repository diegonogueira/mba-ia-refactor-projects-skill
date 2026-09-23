"""Tokens de login assinados com SECRET_KEY (itsdangerous): não dá para forjá-los nem trocar o usuário."""
from flask import current_app
from itsdangerous import BadSignature, URLSafeTimedSerializer

from src.models import usuario_model

SALT_LOGIN = "login"


def _serializador():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=SALT_LOGIN)


def emitir_token(usuario):
    return _serializador().dumps({"usuario_id": usuario["id"]})


def usuario_do_token(token):
    """Usuário atual do token, ou None se o token for inválido, expirado ou de um usuário inexistente."""
    try:
        dados = _serializador().loads(token, max_age=current_app.config["TOKEN_MAX_AGE"])
    except BadSignature:  # inclui SignatureExpired
        return None
    usuario_id = dados.get("usuario_id") if isinstance(dados, dict) else None
    if not isinstance(usuario_id, int):
        return None
    # O tipo é relido do banco: rebaixar um admin vale já no próximo request.
    return usuario_model.buscar_por_id(usuario_id)
