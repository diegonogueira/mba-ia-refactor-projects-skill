import logging
import re

from flask import jsonify, request

from src.utils.errors import ValidationError

logger = logging.getLogger(__name__)

_SELECT_UNICO = re.compile(r"^\s*select\b[^;]*;?\s*$", re.IGNORECASE)


class AdminController:
    """Rotas protegidas por admin_only (desabilitadas por padrão)."""

    def __init__(self, admin_model):
        self._admin = admin_model

    def reset_database(self):
        self._admin.resetar()
        logger.warning("Banco de dados resetado via /admin/reset-db")
        return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200

    def executar_query(self):
        dados = request.get_json(silent=True)
        query = dados.get("sql", "") if isinstance(dados, dict) else ""
        if not query:
            raise ValidationError("Query não informada")
        if not isinstance(query, str) or not _SELECT_UNICO.match(query):
            raise ValidationError("Apenas uma única consulta SELECT é permitida")

        return jsonify({"dados": self._admin.consultar_somente_leitura(query), "sucesso": True}), 200
