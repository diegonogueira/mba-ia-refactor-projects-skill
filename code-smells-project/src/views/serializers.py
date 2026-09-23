"""Representação JSON das entidades: somente campos públicos (allowlist)."""
CAMPOS_PRODUTO = ("id", "nome", "descricao", "preco", "estoque", "categoria", "ativo", "criado_em")
CAMPOS_USUARIO = ("id", "nome", "email", "tipo", "criado_em")
CAMPOS_USUARIO_LOGIN = ("id", "nome", "email", "tipo")
CAMPOS_PEDIDO = ("id", "usuario_id", "status", "total", "criado_em")
CAMPOS_ITEM_PEDIDO = ("produto_id", "produto_nome", "quantidade", "preco_unitario")
PRODUTO_DESCONHECIDO = "Desconhecido"


def _selecionar(registro, campos):
    return {campo: registro[campo] for campo in campos}


def serializar_produto(produto):
    return _selecionar(produto, CAMPOS_PRODUTO)


def serializar_usuario(usuario):
    return _selecionar(usuario, CAMPOS_USUARIO)


def serializar_login(usuario):
    return _selecionar(usuario, CAMPOS_USUARIO_LOGIN)


def _serializar_item(item):
    dados = _selecionar(item, CAMPOS_ITEM_PEDIDO)
    if dados["produto_nome"] is None:
        dados["produto_nome"] = PRODUTO_DESCONHECIDO
    return dados


def serializar_pedido(pedido):
    dados = _selecionar(pedido, CAMPOS_PEDIDO)
    dados["itens"] = [_serializar_item(item) for item in pedido["itens"]]
    return dados
