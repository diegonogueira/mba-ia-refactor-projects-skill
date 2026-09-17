import logging

from flask import jsonify, request

from src.utils.errors import SUCESSO_FALSO, NotFoundError, UnauthorizedError, ValidationError
from src.utils.validators import require_json_object
from src.views.serializers import serializar_usuario, serializar_usuario_login

logger = logging.getLogger(__name__)


class UsuarioController:
    def __init__(self, usuario_model):
        self._usuarios = usuario_model

    def listar_usuarios(self):
        usuarios = self._usuarios.listar()
        return jsonify({"dados": [serializar_usuario(u) for u in usuarios], "sucesso": True}), 200

    def buscar_usuario(self, usuario_id: int):
        usuario = self._usuarios.buscar_por_id(usuario_id)
        if usuario is None:
            raise NotFoundError("Usuário não encontrado")
        return jsonify({"dados": serializar_usuario(usuario), "sucesso": True}), 200

    def criar_usuario(self):
        dados = require_json_object(request.get_json(silent=True))
        nome = dados.get("nome", "")
        email = dados.get("email", "")
        senha = dados.get("senha", "")

        if not nome or not email or not senha:
            raise ValidationError("Nome, email e senha são obrigatórios")
        if not all(isinstance(valor, str) for valor in (nome, email, senha)):
            raise ValidationError("Nome, email e senha devem ser textos")

        usuario_id = self._usuarios.criar(nome, email, senha)
        logger.info("Usuário criado: id=%s", usuario_id)
        return jsonify({"dados": {"id": usuario_id}, "sucesso": True}), 201

    def login(self):
        dados = request.get_json(silent=True)
        if not isinstance(dados, dict):
            raise ValidationError("Dados inválidos")
        email = dados.get("email", "")
        senha = dados.get("senha", "")

        if not email or not senha:
            raise ValidationError("Email e senha são obrigatórios")
        if not isinstance(email, str) or not isinstance(senha, str):
            raise ValidationError("Email e senha devem ser textos")

        usuario = self._usuarios.autenticar(email, senha)
        if usuario is None:
            logger.info("Login falhou")
            raise UnauthorizedError("Email ou senha inválidos", extra=SUCESSO_FALSO)

        logger.info("Login bem-sucedido: usuario_id=%s", usuario["id"])
        return jsonify({"dados": serializar_usuario_login(usuario), "sucesso": True, "mensagem": "Login OK"}), 200
