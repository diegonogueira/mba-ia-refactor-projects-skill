"""Tratamento centralizado de erros: toda falha vira JSON no envelope {"erro": ..., "sucesso": false}."""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from src.utils.errors import AppError

logger = logging.getLogger(__name__)

MENSAGENS_HTTP = {
    400: "Requisição inválida",
    404: "Recurso não encontrado",
    405: "Método não permitido",
    415: "Tipo de conteúdo não suportado",
}
ERRO_INTERNO = "Erro interno do servidor"


def _resposta_erro(mensagem, status):
    return jsonify({"erro": mensagem, "sucesso": False}), status


def _resposta_http_erro(erro):
    """Troca o corpo HTML da HTTPException pelo envelope JSON, preservando os headers do framework.

    Recriar a resposta do zero descartaria headers que fazem parte do contrato HTTP —
    `Allow` no 405, `WWW-Authenticate` no 401, `Retry-After` no 429.
    """
    resposta = erro.get_response()
    corpo = jsonify({"erro": MENSAGENS_HTTP.get(erro.code, erro.name), "sucesso": False})
    resposta.data = corpo.data
    resposta.content_type = corpo.content_type
    return resposta


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def tratar_erro_aplicacao(erro):
        return _resposta_erro(erro.mensagem, erro.status_code)

    @app.errorhandler(HTTPException)
    def tratar_erro_http(erro):
        return _resposta_http_erro(erro)

    @app.errorhandler(Exception)
    def tratar_erro_inesperado(_erro):
        logger.exception("Erro não tratado")
        return _resposta_erro(ERRO_INTERNO, 500)
