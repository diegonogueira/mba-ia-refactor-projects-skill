"""Operações de sistema sobre o banco: contagens do health check e rotinas administrativas."""
import logging
import re
import sqlite3

from src.models.database import DatabaseError, get_connection, get_read_only_connection, transaction
from src.utils.errors import ValidationError

logger = logging.getLogger(__name__)

CONSULTA_SELECT_UNICA = re.compile(r"^\s*select\b[^;]*;?\s*$", re.IGNORECASE)

# Colunas de credenciais nunca saem por /admin/query. O controle efetivo é o authorizer do SQLite
# (`_autorizar_consulta`): ele vê a tabela e a coluna reais de cada leitura, então renomear a coluna
# (`VALUES ... UNION ALL SELECT * FROM usuarios`, aliases, subconsultas) não escapa — o valor vira NULL.
# A recusa pelo texto e a remoção por nome só deixam a resposta mais clara nos casos óbvios (`SELECT *`).
COLUNAS_CREDENCIAIS = frozenset({"senha", "password", "token", "secret"})
REFERENCIA_CREDENCIAL = re.compile(r"\b(%s)\b" % "|".join(sorted(COLUNAS_CREDENCIAIS)), re.IGNORECASE)
# Operações que uma consulta administrativa pode executar; qualquer outra (PRAGMA, ATTACH, escrita) é negada.
ACOES_PERMITIDAS = frozenset({sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION})

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


def _autorizar_consulta(acao, _tabela, coluna, _banco, _origem):
    if acao not in ACOES_PERMITIDAS:
        return sqlite3.SQLITE_DENY
    if acao == sqlite3.SQLITE_READ and coluna and coluna.lower() in COLUNAS_CREDENCIAIS:
        return sqlite3.SQLITE_IGNORE  # a coluna é lida como NULL
    return sqlite3.SQLITE_OK


def _sem_credenciais(linha):
    return {coluna: valor for coluna, valor in dict(linha).items() if coluna.lower() not in COLUNAS_CREDENCIAIS}


def consultar_somente_leitura(sql):
    if not CONSULTA_SELECT_UNICA.match(sql):
        raise ValidationError("Apenas uma única consulta SELECT é permitida")
    if REFERENCIA_CREDENCIAL.search(sql):
        raise ValidationError("Consulta não pode referenciar colunas de credenciais")
    conexao = get_read_only_connection()
    conexao.set_authorizer(_autorizar_consulta)
    try:
        linhas = conexao.execute(sql).fetchall()
    except DatabaseError as erro:
        logger.warning("Consulta administrativa rejeitada: %s", erro)
        raise ValidationError("Consulta inválida") from erro
    finally:
        conexao.close()
    return [_sem_credenciais(linha) for linha in linhas]
