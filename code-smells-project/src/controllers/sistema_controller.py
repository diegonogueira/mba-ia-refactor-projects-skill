import logging

from flask import current_app, jsonify, request

from src.config.settings import API_VERSION
from src.controllers.validators import ler_consulta
from src.models import sistema_model
from src.models.database import DatabaseError

logger = logging.getLogger(__name__)

ENDPOINTS_PUBLICOS = {
    "produtos": "/produtos",
    "usuarios": "/usuarios",
    "pedidos": "/pedidos",
    "login": "/login",
    "relatorios": "/relatorios/vendas",
    "health": "/health",
}


def index():
    return jsonify({"mensagem": "Bem-vindo à API da Loja", "versao": API_VERSION, "endpoints": ENDPOINTS_PUBLICOS})


def health_check():
    try:
        contagens = sistema_model.contar_registros()
    except DatabaseError:
        logger.exception("Health check: falha ao consultar o banco de dados")
        return jsonify({"status": "erro", "detalhes": "Banco de dados indisponível"}), 500
    return jsonify({
        "status": "ok",
        "database": "connected",
        "counts": contagens,
        "versao": API_VERSION,
        "ambiente": current_app.config["APP_ENV"],
    }), 200


def reset_database():
    sistema_model.resetar_banco()
    logger.warning("Banco de dados resetado via /admin/reset-db")
    return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200


def executar_query():
    resultado = sistema_model.consultar_somente_leitura(ler_consulta(request.get_json(silent=True)))
    return jsonify({"dados": resultado, "sucesso": True}), 200
