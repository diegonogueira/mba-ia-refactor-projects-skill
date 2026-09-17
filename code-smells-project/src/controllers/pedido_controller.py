from flask import jsonify, request

from src.models.pedido_model import STATUS_VALIDOS
from src.utils.errors import ValidationError
from src.utils.validators import is_integer, parse_positive_int, require_json_object
from src.views.serializers import serializar_pedido


def validar_item(item) -> dict:
    if not isinstance(item, dict):
        raise ValidationError("Item inválido")
    produto_id = parse_positive_int(item.get("produto_id"))
    if produto_id is None:
        raise ValidationError("Item inválido: produto_id deve ser um inteiro positivo")
    quantidade = item.get("quantidade")
    if not is_integer(quantidade) or quantidade <= 0:
        raise ValidationError("Item inválido: quantidade deve ser um inteiro maior que zero")
    return {"produto_id": produto_id, "quantidade": quantidade}


class PedidoController:
    def __init__(self, pedido_service, pedido_model):
        self._service = pedido_service
        self._pedidos = pedido_model

    def criar_pedido(self):
        dados = require_json_object(request.get_json(silent=True))
        usuario_id = dados.get("usuario_id")
        itens = dados.get("itens", [])

        if not usuario_id:
            raise ValidationError("Usuario ID é obrigatório")
        if not itens:
            raise ValidationError("Pedido deve ter pelo menos 1 item")
        usuario_id = parse_positive_int(usuario_id)
        if usuario_id is None:
            raise ValidationError("Usuario ID inválido")
        if not isinstance(itens, list):
            raise ValidationError("Itens devem ser uma lista")

        resultado = self._service.criar_pedido(usuario_id, [validar_item(item) for item in itens])
        return jsonify({"dados": resultado, "sucesso": True, "mensagem": "Pedido criado com sucesso"}), 201

    def listar_todos_pedidos(self):
        pedidos = self._pedidos.listar()
        return jsonify({"dados": [serializar_pedido(p) for p in pedidos], "sucesso": True}), 200

    def listar_pedidos_usuario(self, usuario_id: int):
        pedidos = self._pedidos.listar(usuario_id=usuario_id)
        return jsonify({"dados": [serializar_pedido(p) for p in pedidos], "sucesso": True}), 200

    def atualizar_status_pedido(self, pedido_id: int):
        dados = request.get_json(silent=True)
        if not isinstance(dados, dict):
            raise ValidationError("Dados inválidos")
        novo_status = dados.get("status", "")
        if novo_status not in STATUS_VALIDOS:
            raise ValidationError("Status inválido")

        self._service.atualizar_status(pedido_id, novo_status)
        return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200
