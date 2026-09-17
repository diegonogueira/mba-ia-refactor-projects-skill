from src.utils.errors import SUCESSO_FALSO, NotFoundError, ValidationError


class PedidoService:
    def __init__(self, pedido_model, usuario_model, notification_service):
        self._pedidos = pedido_model
        self._usuarios = usuario_model
        self._notificacoes = notification_service

    def criar_pedido(self, usuario_id: int, itens: list[dict]) -> dict:
        if not self._usuarios.existe(usuario_id):
            raise ValidationError("Usuário não encontrado", extra=SUCESSO_FALSO)
        resultado = self._pedidos.criar(usuario_id, itens)
        self._notificacoes.pedido_criado(resultado["pedido_id"], usuario_id)
        return resultado

    def atualizar_status(self, pedido_id: int, status: str) -> None:
        if not self._pedidos.atualizar_status(pedido_id, status):
            raise NotFoundError("Pedido não encontrado")
        self._notificacoes.status_pedido_alterado(pedido_id, status)
