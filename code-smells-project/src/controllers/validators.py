"""Leitura e validação dos dados de entrada das requisições (presença e tipos)."""
import math
import re

from src.models.produto_model import CATEGORIA_PADRAO
from src.utils.errors import ValidationError

DADOS_INVALIDOS = "Dados inválidos"
EMAIL_FORMATO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _eh_numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool) and math.isfinite(valor)


def _eh_inteiro(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)


def exigir_objeto_json(dados, permitir_vazio=False):
    if not isinstance(dados, dict) or (not dados and not permitir_vazio):
        raise ValidationError(DADOS_INVALIDOS)
    return dados


def ler_produto(dados):
    dados = exigir_objeto_json(dados)
    for campo, mensagem in (("nome", "Nome é obrigatório"), ("preco", "Preço é obrigatório"),
                            ("estoque", "Estoque é obrigatório")):
        if dados.get(campo) is None:
            raise ValidationError(mensagem)

    descricao = dados.get("descricao") or ""
    if not isinstance(dados["nome"], str):
        raise ValidationError("Nome deve ser um texto")
    if not isinstance(descricao, str):
        raise ValidationError("Descrição deve ser um texto")
    if not _eh_numero(dados["preco"]):
        raise ValidationError("Preço deve ser numérico")
    if not _eh_inteiro(dados["estoque"]):
        raise ValidationError("Estoque deve ser um número inteiro")

    return {
        "nome": dados["nome"],
        "descricao": descricao,
        "preco": dados["preco"],
        "estoque": dados["estoque"],
        "categoria": dados.get("categoria", CATEGORIA_PADRAO),
    }


def ler_filtros_busca(parametros):
    filtros = {"termo": parametros.get("q", ""), "categoria": parametros.get("categoria") or None}
    for campo in ("preco_min", "preco_max"):
        valor = parametros.get(campo)
        if not valor:
            filtros[campo] = None
            continue
        try:
            filtros[campo] = float(valor)
        except ValueError:
            raise ValidationError(f"Parâmetro {campo} deve ser numérico") from None
        if not math.isfinite(filtros[campo]):
            raise ValidationError(f"Parâmetro {campo} deve ser numérico")
    return filtros


def ler_usuario(dados):
    dados = exigir_objeto_json(dados)
    campos = [dados.get(campo, "") for campo in ("nome", "email", "senha")]
    if not all(campos):
        raise ValidationError("Nome, email e senha são obrigatórios")
    if not all(isinstance(valor, str) for valor in campos):
        raise ValidationError("Nome, email e senha devem ser textos")
    nome, email, senha = campos
    if not EMAIL_FORMATO.match(email):
        raise ValidationError("Email inválido")
    return {"nome": nome, "email": email, "senha": senha}


def ler_login(dados):
    dados = exigir_objeto_json(dados, permitir_vazio=True)
    email, senha = dados.get("email", ""), dados.get("senha", "")
    if not email or not senha or not isinstance(email, str) or not isinstance(senha, str):
        raise ValidationError("Email e senha são obrigatórios")
    return {"email": email, "senha": senha}


def ler_pedido(dados):
    dados = exigir_objeto_json(dados)
    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])

    if not usuario_id:
        raise ValidationError("Usuario ID é obrigatório")
    if not _eh_inteiro(usuario_id):
        raise ValidationError("Usuario ID deve ser um número inteiro")
    if not itens:
        raise ValidationError("Pedido deve ter pelo menos 1 item")
    if not isinstance(itens, list):
        raise ValidationError("Itens do pedido devem ser uma lista")

    itens_validos = []
    for item in itens:
        if not isinstance(item, dict) or not _eh_inteiro(item.get("produto_id")) \
                or not _eh_inteiro(item.get("quantidade")):
            raise ValidationError("Item inválido: produto_id e quantidade devem ser números inteiros")
        if item["quantidade"] <= 0:
            raise ValidationError("Quantidade deve ser maior que zero")
        itens_validos.append({"produto_id": item["produto_id"], "quantidade": item["quantidade"]})

    return {"usuario_id": usuario_id, "itens": itens_validos}


def ler_status(dados):
    return exigir_objeto_json(dados, permitir_vazio=True).get("status", "")


def ler_consulta(dados):
    sql = exigir_objeto_json(dados, permitir_vazio=True).get("sql", "")
    if not sql or not isinstance(sql, str):
        raise ValidationError("Query não informada")
    return sql
