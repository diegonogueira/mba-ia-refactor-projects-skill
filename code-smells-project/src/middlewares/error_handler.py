import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from src.utils.errors import AppError

logger = logging.getLogger(__name__)

ERROR_KEY = "erro"
_HTTP_MESSAGES = {
    400: "Dados inválidos",
    404: "Recurso não encontrado",
    405: "Método não permitido",
    415: "Dados inválidos",
}


def register_error_handlers(app) -> None:
    @app.errorhandler(AppError)
    def handle_app_error(err: AppError):
        return jsonify({ERROR_KEY: err.message, **err.extra}), err.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(err: HTTPException):
        response = jsonify({ERROR_KEY: _HTTP_MESSAGES.get(err.code, err.name)})
        response.status_code = err.code
        if getattr(err, "valid_methods", None):
            response.headers["Allow"] = ", ".join(err.valid_methods)
        return response

    @app.errorhandler(Exception)
    def handle_unexpected(err: Exception):
        logger.exception("Erro não tratado")
        return jsonify({ERROR_KEY: "Erro interno do servidor"}), 500
