from flask import jsonify

from src.models import relatorio_model


def relatorio_vendas():
    return jsonify({"dados": relatorio_model.gerar_relatorio_vendas(), "sucesso": True}), 200
