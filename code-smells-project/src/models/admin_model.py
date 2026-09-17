from src.models.database import DatabaseError, transaction
from src.utils.errors import ValidationError

# Tabelas filhas antes das pais, para respeitar as chaves estrangeiras
_RESET_STATEMENTS = (
    "DELETE FROM itens_pedido",
    "DELETE FROM pedidos",
    "DELETE FROM produtos",
    "DELETE FROM usuarios",
)


class AdminModel:
    def __init__(self, get_connection, get_read_only_connection):
        self._get_connection = get_connection
        self._get_read_only_connection = get_read_only_connection

    def resetar(self) -> None:
        conn = self._get_connection()
        with transaction(conn):
            for statement in _RESET_STATEMENTS:
                conn.execute(statement)

    def consultar_somente_leitura(self, select_sql: str) -> list[dict]:
        """Executa um SELECT já validado numa conexão aberta em modo somente leitura."""
        conn = self._get_read_only_connection()
        try:
            return [dict(row) for row in conn.execute(select_sql).fetchall()]
        except DatabaseError as exc:
            raise ValidationError("Query inválida") from exc
        finally:
            conn.close()
