import logging

from flask import jsonify, request

from src.controllers.validators import ler_login, ler_usuario
from src.models import usuario_model
from src.utils.errors import NotFoundError, UnauthorizedError
from src.views.serializers import serializar_login, serializar_usuario

logger = logging.getLogger(__name__)


def listar_usuarios():
    usuarios = usuario_model.listar_todos()
    return jsonify({"dados": [serializar_usuario(usuario) for usuario in usuarios], "sucesso": True}), 200


def buscar_usuario(usuario_id):
    usuario = usuario_model.buscar_por_id(usuario_id)
    if usuario is None:
        raise NotFoundError("Usuário não encontrado")
    return jsonify({"dados": serializar_usuario(usuario), "sucesso": True}), 200


def criar_usuario():
    dados = ler_usuario(request.get_json(silent=True))
    usuario_id = usuario_model.criar(**dados)
    logger.info("Usuário criado: id=%s", usuario_id)
    return jsonify({"dados": {"id": usuario_id}, "sucesso": True}), 201


def login():
    credenciais = ler_login(request.get_json(silent=True))
    usuario = usuario_model.autenticar(credenciais["email"], credenciais["senha"])
    if usuario is None:
        logger.info("Login falhou")
        raise UnauthorizedError("Email ou senha inválidos")
    logger.info("Login bem-sucedido: usuario_id=%s", usuario["id"])
    return jsonify({"dados": serializar_login(usuario), "sucesso": True, "mensagem": "Login OK"}), 200
