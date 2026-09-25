from flask import jsonify, request

from src.controllers.validators import ler_pedido, ler_status
from src.middlewares.auth_guard import exigir_dono_ou_admin
from src.models import pedido_model
from src.services import pedido_service
from src.views.serializers import serializar_pedido


def criar_pedido():
    dados = ler_pedido(request.get_json(silent=True))
    exigir_dono_ou_admin(dados["usuario_id"])
    resultado = pedido_service.criar_pedido(dados["usuario_id"], dados["itens"])
    return jsonify({"dados": resultado, "sucesso": True, "mensagem": "Pedido criado com sucesso"}), 201


def listar_todos_pedidos():
    pedidos = pedido_model.listar()
    return jsonify({"dados": [serializar_pedido(pedido) for pedido in pedidos], "sucesso": True}), 200


def listar_pedidos_usuario(usuario_id):
    pedidos = pedido_model.listar(usuario_id=usuario_id)
    return jsonify({"dados": [serializar_pedido(pedido) for pedido in pedidos], "sucesso": True}), 200


def atualizar_status_pedido(pedido_id):
    pedido_service.atualizar_status(pedido_id, ler_status(request.get_json(silent=True)))
    return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200
