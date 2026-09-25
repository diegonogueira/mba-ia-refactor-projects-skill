"""Tratamento de erros centralizado: toda resposta de erro sai em JSON, no mesmo envelope."""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from src.utils.errors import AppError

logger = logging.getLogger(__name__)

ERROR_KEY = 'error'
INTERNAL_ERROR_MESSAGE = 'Erro interno'
HTTP_ERROR_MESSAGES = {
    400: 'Requisição inválida',
    404: 'Recurso não encontrado',
    405: 'Método não permitido',
    415: 'Tipo de conteúdo não suportado',
}


def register_error_handlers(app) -> None:
    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        return jsonify({ERROR_KEY: error.message}), error.status_code, error.headers

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        response = jsonify({ERROR_KEY: HTTP_ERROR_MESSAGES.get(error.code, error.description)})
        response.status_code = error.code
        for name, value in error.get_headers():
            if name.lower() != 'content-type':
                response.headers[name] = value
        return response

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        logger.exception('Erro não tratado')
        return jsonify({ERROR_KEY: INTERNAL_ERROR_MESSAGE}), 500
