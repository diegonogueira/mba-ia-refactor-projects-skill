"""Notificações disparadas pelos casos de uso de pedido (simuladas via log)."""
import logging

from src.models.status_pedido import STATUS_APROVADO, STATUS_CANCELADO

logger = logging.getLogger(__name__)


def pedido_criado(pedido_id, usuario_id):
    logger.info("ENVIANDO EMAIL: Pedido %s criado para usuario %s", pedido_id, usuario_id)
    logger.info("ENVIANDO SMS: Seu pedido foi recebido!")
    logger.info("ENVIANDO PUSH: Novo pedido recebido pelo sistema")


def status_pedido_alterado(pedido_id, novo_status):
    if novo_status == STATUS_APROVADO:
        logger.info("NOTIFICAÇÃO: Pedido %s foi aprovado! Preparar envio.", pedido_id)
    elif novo_status == STATUS_CANCELADO:
        logger.info("NOTIFICAÇÃO: Pedido %s cancelado. Estoque devolvido.", pedido_id)
