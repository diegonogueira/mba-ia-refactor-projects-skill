"""Acesso a dados e regras da entidade pedido (e seus itens)."""
from src.models.database import get_connection, transaction
from src.utils.errors import NotFoundError, ValidationError

STATUS_PENDENTE = "pendente"
STATUS_APROVADO = "aprovado"
STATUS_ENVIADO = "enviado"
STATUS_ENTREGUE = "entregue"
STATUS_CANCELADO = "cancelado"
STATUS_VALIDOS = (STATUS_PENDENTE, STATUS_APROVADO, STATUS_ENVIADO, STATUS_ENTREGUE, STATUS_CANCELADO)
ESTADOS_FINAIS = (STATUS_CANCELADO, STATUS_ENTREGUE)

# Soma de volta a cada produto as quantidades de todos os itens do pedido (um produto pode repetir).
SQL_DEVOLVER_ESTOQUE = """
    UPDATE produtos
    SET estoque = estoque + (SELECT SUM(i.quantidade) FROM itens_pedido i
                             WHERE i.pedido_id = ? AND i.produto_id = produtos.id)
    WHERE id IN (SELECT produto_id FROM itens_pedido WHERE pedido_id = ?)
"""

SQL_PEDIDOS_COM_ITENS = """
    SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
           i.id AS item_id, i.produto_id, i.quantidade, i.preco_unitario, pr.nome AS produto_nome
    FROM pedidos p
    LEFT JOIN itens_pedido i ON i.pedido_id = p.id
    LEFT JOIN produtos pr ON pr.id = i.produto_id
"""


def _carregar_produtos(conexao, produto_ids):
    ids = sorted(set(produto_ids))
    marcadores = ", ".join("?" * len(ids))
    linhas = conexao.execute(f"SELECT id, nome, preco, estoque FROM produtos WHERE id IN ({marcadores})", ids)
    return {linha["id"]: linha for linha in linhas}


def criar(usuario_id, itens):
    """Valida estoque, grava pedido e itens e baixa o estoque numa única transação.

    BEGIN IMMEDIATE bloqueia outros escritores durante a verificação, evitando venda acima do estoque.
    """
    with transaction(immediate=True) as conexao:
        produtos = _carregar_produtos(conexao, [item["produto_id"] for item in itens])

        total = 0
        quantidade_por_produto = {}
        for item in itens:
            produto = produtos.get(item["produto_id"])
            if produto is None:
                raise ValidationError(f"Produto {item['produto_id']} não encontrado")
            quantidade_por_produto[produto["id"]] = quantidade_por_produto.get(produto["id"], 0) + item["quantidade"]
            if produto["estoque"] < quantidade_por_produto[produto["id"]]:
                raise ValidationError(f"Estoque insuficiente para {produto['nome']}")
            total = total + produto["preco"] * item["quantidade"]

        if conexao.execute("SELECT 1 FROM usuarios WHERE id = ?", (usuario_id,)).fetchone() is None:
            raise ValidationError(f"Usuário {usuario_id} não encontrado")

        pedido_id = conexao.execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
            (usuario_id, STATUS_PENDENTE, total),
        ).lastrowid
        conexao.executemany(
            "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
            [(pedido_id, item["produto_id"], item["quantidade"], produtos[item["produto_id"]]["preco"])
             for item in itens],
        )
        baixados = conexao.executemany(
            "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
            [(item["quantidade"], item["produto_id"], item["quantidade"]) for item in itens],
        ).rowcount
        if baixados != len(itens):
            raise ValidationError("Estoque insuficiente")

    return {"pedido_id": pedido_id, "total": total}


def listar(usuario_id=None):
    sql, parametros = SQL_PEDIDOS_COM_ITENS, ()
    if usuario_id is not None:
        sql, parametros = sql + " WHERE p.usuario_id = ?", (usuario_id,)
    linhas = get_connection().execute(sql + " ORDER BY p.id, i.id", parametros).fetchall()

    pedidos = {}
    for linha in linhas:
        pedido = pedidos.setdefault(linha["id"], {
            "id": linha["id"],
            "usuario_id": linha["usuario_id"],
            "status": linha["status"],
            "total": linha["total"],
            "criado_em": linha["criado_em"],
            "itens": [],
        })
        if linha["item_id"] is not None:
            pedido["itens"].append({
                "produto_id": linha["produto_id"],
                "produto_nome": linha["produto_nome"],
                "quantidade": linha["quantidade"],
                "preco_unitario": linha["preco_unitario"],
            })
    return list(pedidos.values())


def atualizar_status(pedido_id, novo_status):
    """Muda o status e retorna o anterior. Cancelar devolve o estoque dos itens, exatamente uma vez.

    Cancelado e entregue são estados finais: sair deles reservaria de novo (ou devolveria)
    um estoque que já foi compensado. Repetir o status atual não altera nada.
    """
    if novo_status not in STATUS_VALIDOS:
        raise ValidationError("Status inválido")
    with transaction(immediate=True) as conexao:
        linha = conexao.execute("SELECT status FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
        if linha is None:
            raise NotFoundError("Pedido não encontrado")
        anterior = linha["status"]
        if anterior == novo_status:
            return anterior
        if anterior in ESTADOS_FINAIS:
            raise ValidationError(f"Pedido {anterior} não pode mudar de status")

        alterados = conexao.execute(
            "UPDATE pedidos SET status = ? WHERE id = ? AND status = ?", (novo_status, pedido_id, anterior)
        ).rowcount
        if alterados and novo_status == STATUS_CANCELADO:
            conexao.execute(SQL_DEVOLVER_ESTOQUE, (pedido_id, pedido_id))
    return anterior
