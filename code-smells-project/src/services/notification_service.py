import logging

from src.models.pedido_model import STATUS_APROVADO, STATUS_CANCELADO

logger = logging.getLogger(__name__)


class NotificationService:
    """Notificações simuladas via log; ponto único para plugar e-mail, SMS e push reais."""

    def pedido_criado(self, pedido_id: int, usuario_id: int) -> None:
        logger.info("ENVIANDO EMAIL: Pedido %s criado para usuario %s", pedido_id, usuario_id)
        logger.info("ENVIANDO SMS: Seu pedido foi recebido!")
        logger.info("ENVIANDO PUSH: Novo pedido recebido pelo sistema")

    def status_pedido_alterado(self, pedido_id: int, status: str) -> None:
        if status == STATUS_APROVADO:
            logger.info("NOTIFICAÇÃO: Pedido %s foi aprovado! Preparar envio.", pedido_id)
        elif status == STATUS_CANCELADO:
            logger.info("NOTIFICAÇÃO: Pedido %s cancelado. Devolver estoque.", pedido_id)
