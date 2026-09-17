import logging

from flask import jsonify, request

from src.models.produto_model import CATEGORIA_PADRAO, CATEGORIAS_VALIDAS, NOME_MAX_CARACTERES, NOME_MIN_CARACTERES
from src.utils.errors import SUCESSO_FALSO, NotFoundError, ValidationError
from src.utils.validators import is_integer, is_number, parse_optional_float, require_json_object
from src.views.serializers import serializar_produto

logger = logging.getLogger(__name__)

_CAMPOS_OBRIGATORIOS = (
    ("nome", "Nome é obrigatório"),
    ("preco", "Preço é obrigatório"),
    ("estoque", "Estoque é obrigatório"),
)


def validar_produto(payload) -> dict:
    """Mesmas regras para criação e atualização."""
    dados = require_json_object(payload)
    for campo, mensagem in _CAMPOS_OBRIGATORIOS:
        if campo not in dados:
            raise ValidationError(mensagem)

    nome = dados["nome"]
    descricao = dados.get("descricao", "")
    preco = dados["preco"]
    estoque = dados["estoque"]
    categoria = dados.get("categoria", CATEGORIA_PADRAO)

    if not isinstance(nome, str):
        raise ValidationError("Nome deve ser um texto")
    if not isinstance(descricao, str):
        raise ValidationError("Descrição deve ser um texto")
    if not is_number(preco):
        raise ValidationError("Preço deve ser numérico")
    if not is_integer(estoque):
        raise ValidationError("Estoque deve ser um número inteiro")
    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")
    if len(nome) < NOME_MIN_CARACTERES:
        raise ValidationError("Nome muito curto")
    if len(nome) > NOME_MAX_CARACTERES:
        raise ValidationError("Nome muito longo")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError("Categoria inválida. Válidas: " + str(list(CATEGORIAS_VALIDAS)))

    return {"nome": nome, "descricao": descricao, "preco": preco, "estoque": estoque, "categoria": categoria}


class ProdutoController:
    def __init__(self, produto_model):
        self._produtos = produto_model

    def listar_produtos(self):
        produtos = self._produtos.listar()
        logger.info("Listando %s produtos", len(produtos))
        return jsonify({"dados": [serializar_produto(p) for p in produtos], "sucesso": True}), 200

    def buscar_produto(self, produto_id: int):
        produto = self._produtos.buscar_por_id(produto_id)
        if produto is None:
            raise NotFoundError("Produto não encontrado", extra=SUCESSO_FALSO)
        return jsonify({"dados": serializar_produto(produto), "sucesso": True}), 200

    def buscar_produtos(self):
        termo = request.args.get("q", "")
        categoria = request.args.get("categoria")
        preco_min = parse_optional_float(request.args.get("preco_min"), "Parâmetro preco_min inválido")
        preco_max = parse_optional_float(request.args.get("preco_max"), "Parâmetro preco_max inválido")

        resultados = self._produtos.buscar(termo, categoria, preco_min, preco_max)
        return jsonify({
            "dados": [serializar_produto(p) for p in resultados],
            "total": len(resultados),
            "sucesso": True,
        }), 200

    def criar_produto(self):
        produto = validar_produto(request.get_json(silent=True))
        produto_id = self._produtos.criar(**produto)
        logger.info("Produto criado com ID: %s", produto_id)
        return jsonify({"dados": {"id": produto_id}, "sucesso": True, "mensagem": "Produto criado"}), 201

    def atualizar_produto(self, produto_id: int):
        payload = request.get_json(silent=True)
        if self._produtos.buscar_por_id(produto_id) is None:
            raise NotFoundError("Produto não encontrado")
        self._produtos.atualizar(produto_id, **validar_produto(payload))
        return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200

    def deletar_produto(self, produto_id: int):
        if self._produtos.buscar_por_id(produto_id) is None:
            raise NotFoundError("Produto não encontrado")
        self._produtos.remover(produto_id)
        logger.info("Produto %s deletado", produto_id)
        return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200
