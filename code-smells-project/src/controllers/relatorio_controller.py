from flask import jsonify


class RelatorioController:
    def __init__(self, relatorio_model):
        self._relatorios = relatorio_model

    def relatorio_vendas(self):
        return jsonify({"dados": self._relatorios.vendas(), "sucesso": True}), 200
