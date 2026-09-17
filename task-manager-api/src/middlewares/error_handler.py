"""Centralized error handling: every error leaves the API as {"error": <message>}."""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException, MethodNotAllowed

from src.utils.errors import AppError

logger = logging.getLogger(__name__)

ERROR_KEY = "error"
INTERNAL_ERROR_MESSAGE = "Erro interno"
HTTP_ERROR_MESSAGES = {
    400: "Requisição inválida",
    404: "Recurso não encontrado",
    405: "Método não permitido",
    415: "Tipo de conteúdo não suportado",
}


def register_error_handlers(app) -> None:
    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        return jsonify({ERROR_KEY: error.message}), error.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        response = jsonify({ERROR_KEY: HTTP_ERROR_MESSAGES.get(error.code, error.description)})
        response.status_code = error.code
        if isinstance(error, MethodNotAllowed) and error.valid_methods:
            response.headers["Allow"] = ", ".join(error.valid_methods)
        return response

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        logger.exception("Unhandled error: %s", type(error).__name__)
        return jsonify({ERROR_KEY: INTERNAL_ERROR_MESSAGE}), 500
