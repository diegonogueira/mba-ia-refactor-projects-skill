"""Operações de sistema sobre o banco: contagens do health check e rotinas administrativas."""
import logging
import re

from src.models.database import DatabaseError, get_connection, get_read_only_connection, transaction
from src.utils.errors import ValidationError

logger = logging.getLogger(__name__)

CONSULTA_SELECT_UNICA = re.compile(r"^\s*select\b[^;]*;?\s*$", re.IGNORECASE)

# Ordem respeita as referências entre tabelas (filhos antes dos pais).
COMANDOS_RESET = (
    "DELETE FROM itens_pedido",
    "DELETE FROM pedidos",
    "DELETE FROM produtos",
    "DELETE FROM usuarios",
)


def contar_registros():
    linha = get_connection().execute(
        """
        SELECT (SELECT COUNT(*) FROM produtos) AS produtos,
               (SELECT COUNT(*) FROM usuarios) AS usuarios,
               (SELECT COUNT(*) FROM pedidos) AS pedidos
        """
    ).fetchone()
    return dict(linha)


def resetar_banco():
    with transaction(immediate=True) as conexao:
        for comando in COMANDOS_RESET:
            conexao.execute(comando)


def consultar_somente_leitura(sql):
    if not CONSULTA_SELECT_UNICA.match(sql):
        raise ValidationError("Apenas uma única consulta SELECT é permitida")
    conexao = get_read_only_connection()
    try:
        linhas = conexao.execute(sql).fetchall()
    except DatabaseError as erro:
        logger.warning("Consulta administrativa rejeitada: %s", erro)
        raise ValidationError("Consulta inválida") from erro
    finally:
        conexao.close()
    return [dict(linha) for linha in linhas]
