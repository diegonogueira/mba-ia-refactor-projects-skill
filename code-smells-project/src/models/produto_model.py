from src.models.database import transaction
from src.utils.errors import ConflictError

CATEGORIAS_VALIDAS = ("informatica", "moveis", "vestuario", "geral", "eletronicos", "livros")
CATEGORIA_PADRAO = "geral"
NOME_MIN_CARACTERES = 2
NOME_MAX_CARACTERES = 200

_SELECT_PRODUTO = "SELECT id, nome, descricao, preco, estoque, categoria, ativo, criado_em FROM produtos"


class ProdutoModel:
    def __init__(self, get_connection):
        self._get_connection = get_connection

    def listar(self) -> list[dict]:
        rows = self._get_connection().execute(_SELECT_PRODUTO).fetchall()
        return [dict(row) for row in rows]

    def buscar_por_id(self, produto_id: int) -> dict | None:
        row = self._get_connection().execute(_SELECT_PRODUTO + " WHERE id = ?", (produto_id,)).fetchone()
        return dict(row) if row else None

    def buscar(self, termo: str = "", categoria: str | None = None,
               preco_min: float | None = None, preco_max: float | None = None) -> list[dict]:
        clauses, params = ["1=1"], []
        if termo:
            clauses.append("(nome LIKE ? OR descricao LIKE ?)")
            params += [f"%{termo}%", f"%{termo}%"]
        if categoria:
            clauses.append("categoria = ?")
            params.append(categoria)
        if preco_min is not None:
            clauses.append("preco >= ?")
            params.append(preco_min)
        if preco_max is not None:
            clauses.append("preco <= ?")
            params.append(preco_max)
        sql = _SELECT_PRODUTO + " WHERE " + " AND ".join(clauses)  # só fragmentos constantes; valores vão em params
        rows = self._get_connection().execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def criar(self, nome: str, descricao: str, preco: float, estoque: int, categoria: str) -> int:
        cursor = self._get_connection().execute(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
            (nome, descricao, preco, estoque, categoria),
        )
        return cursor.lastrowid

    def atualizar(self, produto_id: int, nome: str, descricao: str, preco: float, estoque: int, categoria: str) -> None:
        self._get_connection().execute(
            "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
            (nome, descricao, preco, estoque, categoria, produto_id),
        )

    def remover(self, produto_id: int) -> None:
        conn = self._get_connection()
        with transaction(conn):
            possui_pedidos = conn.execute(
                "SELECT 1 FROM itens_pedido WHERE produto_id = ? LIMIT 1", (produto_id,)
            ).fetchone()
            if possui_pedidos:
                raise ConflictError("Produto possui pedidos e não pode ser removido")
            conn.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
