"""Token de login: assinado com SECRET_KEY, com validade, carregando apenas o id do usuário.

O papel (tipo) nunca vai no token: o guard o lê do banco a cada requisição.
"""
from flask import current_app
from itsdangerous import BadSignature, URLSafeTimedSerializer

SALT = "login-token"


def _serializador():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=SALT)


def emitir(usuario_id):
    return _serializador().dumps({"usuario_id": usuario_id})


def ler_usuario_id(token):
    """Id do usuário do token, ou None se ele for inválido, adulterado ou expirado."""
    try:
        dados = _serializador().loads(token, max_age=current_app.config["TOKEN_MAX_AGE"])
    except BadSignature:  # SignatureExpired é subclasse de BadSignature
        return None
    usuario_id = dados.get("usuario_id") if isinstance(dados, dict) else None
    return usuario_id if isinstance(usuario_id, int) and not isinstance(usuario_id, bool) else None
