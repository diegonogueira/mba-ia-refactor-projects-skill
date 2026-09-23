"""Tratamento centralizado de erros: toda falha vira JSON no envelope {"erro": ..., "sucesso": false}."""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from src.utils.errors import AppError

logger = logging.getLogger(__name__)

HTTP_MESSAGES = {
    400: "Requisição inválida",
    404: "Recurso não encontrado",
    405: "Método não permitido",
    415: "Tipo de conteúdo não suportado",
}
INTERNAL_ERROR_MESSAGE = "Erro interno do servidor"


def _error_response(message, status):
    return jsonify({"erro": message, "sucesso": False}), status


def _http_error_response(error):
    """Troca o corpo HTML da HTTPException pelo envelope JSON, preservando os headers do framework.

    Recriar a resposta do zero descartaria headers que fazem parte do contrato HTTP —
    `Allow` no 405, `WWW-Authenticate` no 401, `Retry-After` no 429.
    """
    response = error.get_response()
    body = jsonify({"erro": HTTP_MESSAGES.get(error.code, error.name), "sucesso": False})
    response.data = body.data
    response.content_type = body.content_type
    return response


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(error):
        return _error_response(error.message, error.status_code)

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return _http_error_response(error)

    @app.errorhandler(Exception)
    def handle_unexpected_error(_error):
        logger.exception("Erro não tratado")
        return _error_response(INTERNAL_ERROR_MESSAGE, 500)
