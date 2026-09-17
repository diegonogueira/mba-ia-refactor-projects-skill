"""Acesso a dados e regras da entidade produto."""
from src.models.database import get_connection, transaction
from src.utils.errors import ConflictError, ValidationError

CATEGORIAS_VALIDAS = ("informatica", "moveis", "vestuario", "geral", "eletronicos", "livros")
CATEGORIA_PADRAO = "geral"
NOME_TAMANHO_MINIMO = 2
NOME_TAMANHO_MAXIMO = 200

COLUNAS = "id, nome, descricao, preco, estoque, categoria, ativo, criado_em"


def validar(nome, preco, estoque, categoria):
    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")
    if len(nome) < NOME_TAMANHO_MINIMO:
        raise ValidationError("Nome muito curto")
    if len(nome) > NOME_TAMANHO_MAXIMO:
        raise ValidationError("Nome muito longo")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError("Categoria inválida. Válidas: " + str(list(CATEGORIAS_VALIDAS)))


def listar_todos():
    linhas = get_connection().execute(f"SELECT {COLUNAS} FROM produtos").fetchall()
    return [dict(linha) for linha in linhas]


def buscar_por_id(produto_id):
    linha = get_connection().execute(f"SELECT {COLUNAS} FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    return dict(linha) if linha else None


def buscar(termo=None, categoria=None, preco_min=None, preco_max=None):
    condicoes, parametros = ["1=1"], []
    if termo:
        condicoes.append("(nome LIKE ? OR descricao LIKE ?)")
        parametros += [f"%{termo}%", f"%{termo}%"]
    if categoria:
        condicoes.append("categoria = ?")
        parametros.append(categoria)
    if preco_min is not None:
        condicoes.append("preco >= ?")
        parametros.append(preco_min)
    if preco_max is not None:
        condicoes.append("preco <= ?")
        parametros.append(preco_max)
    # Apenas fragmentos constantes são concatenados; todos os valores vão em `parametros`.
    sql = f"SELECT {COLUNAS} FROM produtos WHERE " + " AND ".join(condicoes)
    return [dict(linha) for linha in get_connection().execute(sql, parametros).fetchall()]


def criar(nome, descricao, preco, estoque, categoria):
    validar(nome, preco, estoque, categoria)
    with transaction() as conexao:
        cursor = conexao.execute(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
            (nome, descricao, preco, estoque, categoria),
        )
    return cursor.lastrowid


def atualizar(produto_id, nome, descricao, preco, estoque, categoria):
    validar(nome, preco, estoque, categoria)
    with transaction() as conexao:
        conexao.execute(
            "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
            (nome, descricao, preco, estoque, categoria, produto_id),
        )


def deletar(produto_id):
    with transaction(immediate=True) as conexao:
        referenciado = conexao.execute(
            "SELECT 1 FROM itens_pedido WHERE produto_id = ? LIMIT 1", (produto_id,)
        ).fetchone()
        if referenciado:
            raise ConflictError("Produto possui pedidos e não pode ser removido")
        conexao.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
