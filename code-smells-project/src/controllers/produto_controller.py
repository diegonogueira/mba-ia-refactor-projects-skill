import logging

from flask import jsonify, request

from src.controllers.validators import ler_filtros_busca, ler_produto
from src.models import produto_model
from src.utils.errors import NotFoundError
from src.views.serializers import serializar_produto

logger = logging.getLogger(__name__)

PRODUTO_NAO_ENCONTRADO = "Produto não encontrado"


def _obter_produto(produto_id):
    produto = produto_model.buscar_por_id(produto_id)
    if produto is None:
        raise NotFoundError(PRODUTO_NAO_ENCONTRADO)
    return produto


def listar_produtos():
    produtos = produto_model.listar_todos()
    logger.info("Listando %s produtos", len(produtos))
    return jsonify({"dados": [serializar_produto(produto) for produto in produtos], "sucesso": True}), 200


def buscar_produtos():
    resultados = produto_model.buscar(**ler_filtros_busca(request.args))
    return jsonify({
        "dados": [serializar_produto(produto) for produto in resultados],
        "total": len(resultados),
        "sucesso": True,
    }), 200


def buscar_produto(produto_id):
    return jsonify({"dados": serializar_produto(_obter_produto(produto_id)), "sucesso": True}), 200


def criar_produto():
    dados = ler_produto(request.get_json(silent=True))
    produto_id = produto_model.criar(**dados)
    logger.info("Produto criado com ID: %s", produto_id)
    return jsonify({"dados": {"id": produto_id}, "sucesso": True, "mensagem": "Produto criado"}), 201


def atualizar_produto(produto_id):
    _obter_produto(produto_id)
    dados = ler_produto(request.get_json(silent=True))
    produto_model.atualizar(produto_id, **dados)
    return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200


def deletar_produto(produto_id):
    _obter_produto(produto_id)
    produto_model.deletar(produto_id)
    logger.info("Produto %s deletado", produto_id)
    return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200
