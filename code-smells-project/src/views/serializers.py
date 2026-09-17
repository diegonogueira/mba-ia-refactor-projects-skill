"""Representação pública das entidades (allowlist de campos)."""

CAMPOS_PRODUTO = ("id", "nome", "descricao", "preco", "estoque", "categoria", "ativo", "criado_em")
CAMPOS_USUARIO = ("id", "nome", "email", "tipo", "criado_em")
CAMPOS_USUARIO_LOGIN = ("id", "nome", "email", "tipo")
CAMPOS_PEDIDO = ("id", "usuario_id", "status", "total", "criado_em")
CAMPOS_ITEM_PEDIDO = ("produto_id", "produto_nome", "quantidade", "preco_unitario")


def _selecionar(registro: dict, campos: tuple[str, ...]) -> dict:
    return {campo: registro[campo] for campo in campos}


def serializar_produto(produto: dict) -> dict:
    return _selecionar(produto, CAMPOS_PRODUTO)


def serializar_usuario(usuario: dict) -> dict:
    return _selecionar(usuario, CAMPOS_USUARIO)


def serializar_usuario_login(usuario: dict) -> dict:
    return _selecionar(usuario, CAMPOS_USUARIO_LOGIN)


def serializar_pedido(pedido: dict) -> dict:
    return {
        **_selecionar(pedido, CAMPOS_PEDIDO),
        "itens": [_selecionar(item, CAMPOS_ITEM_PEDIDO) for item in pedido["itens"]],
    }
