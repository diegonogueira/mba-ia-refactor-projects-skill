"""Operações de sistema sobre o banco: contagens do health check e rotinas administrativas."""
import logging
import re
import sqlite3

from src.models.database import DatabaseError, get_connection, get_read_only_connection, transaction
from src.utils.errors import ValidationError

logger = logging.getLogger(__name__)

CONSULTA_SELECT_UNICA = re.compile(r"^\s*select\b[^;]*;?\s*$", re.IGNORECASE)

# Colunas de credenciais nunca saem por /admin/query. A garantia é o authorizer do SQLite, que
# troca toda leitura dessas colunas por NULL — vale para `SELECT *`, aliases, subconsultas e UNION,
# cujos nomes de coluna vêm do primeiro SELECT. A recusa por texto e a remoção por nome de coluna
# ficam como defesa adicional.
COLUNAS_CREDENCIAIS = frozenset({"senha", "password", "token", "secret"})
REFERENCIA_CREDENCIAL = re.compile(r"\b(%s)\b" % "|".join(sorted(COLUNAS_CREDENCIAIS)), re.IGNORECASE)
ACOES_DE_LEITURA = frozenset({sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION})

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


def _autorizar_leitura(acao, _tabela, coluna, _banco, _origem):
    if acao == sqlite3.SQLITE_READ and coluna and coluna.lower() in COLUNAS_CREDENCIAIS:
        return sqlite3.SQLITE_IGNORE
    return sqlite3.SQLITE_OK if acao in ACOES_DE_LEITURA else sqlite3.SQLITE_DENY


def _sem_credenciais(linha):
    return {coluna: valor for coluna, valor in dict(linha).items() if coluna.lower() not in COLUNAS_CREDENCIAIS}


def consultar_somente_leitura(sql):
    if not CONSULTA_SELECT_UNICA.match(sql):
        raise ValidationError("Apenas uma única consulta SELECT é permitida")
    if REFERENCIA_CREDENCIAL.search(sql):
        raise ValidationError("Consulta não pode referenciar colunas de credenciais")
    conexao = get_read_only_connection()
    conexao.set_authorizer(_autorizar_leitura)
    try:
        linhas = conexao.execute(sql).fetchall()
    except DatabaseError as erro:
        logger.warning("Consulta administrativa rejeitada: %s", erro)
        raise ValidationError("Consulta inválida") from erro
    finally:
        conexao.close()
    return [_sem_credenciais(linha) for linha in linhas]
