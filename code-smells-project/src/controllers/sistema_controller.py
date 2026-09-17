import logging

from flask import jsonify

from src.models.database import DatabaseError

logger = logging.getLogger(__name__)

VERSAO_API = "1.0.0"


class SistemaController:
    def __init__(self, sistema_model, ambiente: str):
        self._sistema = sistema_model
        self._ambiente = ambiente

    def index(self):
        return jsonify({
            "mensagem": "Bem-vindo à API da Loja",
            "versao": VERSAO_API,
            "endpoints": {
                "produtos": "/produtos",
                "usuarios": "/usuarios",
                "pedidos": "/pedidos",
                "login": "/login",
                "relatorios": "/relatorios/vendas",
                "health": "/health",
            },
        })

    def health_check(self):
        try:
            counts = self._sistema.contagens()
        except DatabaseError:
            logger.exception("Health check: banco de dados indisponível")
            return jsonify({"status": "erro", "detalhes": "Banco de dados indisponível"}), 500

        return jsonify({
            "status": "ok",
            "database": "connected",
            "counts": counts,
            "versao": VERSAO_API,
            "ambiente": self._ambiente,
        }), 200
