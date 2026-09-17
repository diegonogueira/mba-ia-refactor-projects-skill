from src.models.database import transaction
from src.utils.errors import SUCESSO_FALSO, ValidationError

STATUS_PENDENTE = "pendente"
STATUS_APROVADO = "aprovado"
STATUS_ENVIADO = "enviado"
STATUS_ENTREGUE = "entregue"
STATUS_CANCELADO = "cancelado"
STATUS_VALIDOS = (STATUS_PENDENTE, STATUS_APROVADO, STATUS_ENVIADO, STATUS_ENTREGUE, STATUS_CANCELADO)

PRODUTO_DESCONHECIDO = "Desconhecido"

_SELECT_PEDIDOS_COM_ITENS = """
    SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
           i.id AS item_id, i.produto_id, i.quantidade, i.preco_unitario,
           pr.id AS produto_encontrado, pr.nome AS produto_nome
    FROM pedidos p
    LEFT JOIN itens_pedido i ON i.pedido_id = p.id
    LEFT JOIN produtos pr ON pr.id = i.produto_id
"""


class PedidoModel:
    def __init__(self, get_connection):
        self._get_connection = get_connection

    def criar(self, usuario_id: int, itens: list[dict]) -> dict:
        """Cria o pedido, os itens e baixa o estoque numa única transação.

        `itens` já validados: [{"produto_id": int, "quantidade": int > 0}, ...].
        """
        conn = self._get_connection()
        with transaction(conn):
            produtos = self._carregar_produtos(conn, {item["produto_id"] for item in itens})
            total = 0
            quantidade_por_produto = {}
            for item in itens:
                produto = produtos.get(item["produto_id"])
                if produto is None:
                    raise ValidationError(f"Produto {item['produto_id']} não encontrado", extra=SUCESSO_FALSO)
                solicitado = quantidade_por_produto.get(produto["id"], 0) + item["quantidade"]
                quantidade_por_produto[produto["id"]] = solicitado
                if produto["estoque"] < solicitado:
                    raise ValidationError(f"Estoque insuficiente para {produto['nome']}", extra=SUCESSO_FALSO)
                total = total + (produto["preco"] * item["quantidade"])

            pedido_id = conn.execute(
                "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
                (usuario_id, STATUS_PENDENTE, total),
            ).lastrowid
            for item in itens:
                produto = produtos[item["produto_id"]]
                conn.execute(
                    "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
                    (pedido_id, produto["id"], item["quantidade"], produto["preco"]),
                )
                baixa = conn.execute(
                    "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
                    (item["quantidade"], produto["id"], item["quantidade"]),
                )
                if baixa.rowcount == 0:
                    raise ValidationError(f"Estoque insuficiente para {produto['nome']}", extra=SUCESSO_FALSO)
        return {"pedido_id": pedido_id, "total": total}

    @staticmethod
    def _carregar_produtos(conn, produto_ids: set[int]) -> dict[int, dict]:
        placeholders = ", ".join("?" for _ in produto_ids)
        sql = "SELECT id, nome, preco, estoque FROM produtos WHERE id IN (" + placeholders + ")"
        return {row["id"]: dict(row) for row in conn.execute(sql, tuple(produto_ids)).fetchall()}

    def listar(self, usuario_id: int | None = None) -> list[dict]:
        sql, params = _SELECT_PEDIDOS_COM_ITENS, ()
        if usuario_id is not None:
            sql += " WHERE p.usuario_id = ?"
            params = (usuario_id,)
        rows = self._get_connection().execute(sql + " ORDER BY p.id, i.id", params).fetchall()

        pedidos = {}
        for row in rows:
            pedido = pedidos.get(row["id"])
            if pedido is None:
                pedido = pedidos[row["id"]] = {
                    "id": row["id"],
                    "usuario_id": row["usuario_id"],
                    "status": row["status"],
                    "total": row["total"],
                    "criado_em": row["criado_em"],
                    "itens": [],
                }
            if row["item_id"] is not None:
                pedido["itens"].append({
                    "produto_id": row["produto_id"],
                    "produto_nome": row["produto_nome"] if row["produto_encontrado"] is not None else PRODUTO_DESCONHECIDO,
                    "quantidade": row["quantidade"],
                    "preco_unitario": row["preco_unitario"],
                })
        return list(pedidos.values())

    def atualizar_status(self, pedido_id: int, status: str) -> bool:
        cursor = self._get_connection().execute("UPDATE pedidos SET status = ? WHERE id = ?", (status, pedido_id))
        return cursor.rowcount > 0
