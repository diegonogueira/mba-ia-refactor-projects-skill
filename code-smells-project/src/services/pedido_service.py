"""Casos de uso de pedido: gravação no model seguida das notificações."""
from src.models import pedido_model
from src.services import notificacao_service


def criar_pedido(usuario_id, itens):
    resultado = pedido_model.criar(usuario_id, itens)
    notificacao_service.pedido_criado(resultado["pedido_id"], usuario_id)
    return resultado


def atualizar_status(pedido_id, novo_status):
    pedido_model.atualizar_status(pedido_id, novo_status)
    notificacao_service.status_pedido_alterado(pedido_id, novo_status)
