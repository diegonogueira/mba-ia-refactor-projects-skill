from flask import Blueprint

from src.controllers import pedido_controller as controller
from src.middlewares.auth_guard import admin_required, login_required, owner_or_admin

pedido_bp = Blueprint("pedidos", __name__)

# Criar pedido exige login; o controller confere se o usuario_id do corpo é o do token (ou se é admin).
pedido_bp.add_url_rule("/pedidos", "criar_pedido", login_required(controller.criar_pedido), methods=["POST"])
pedido_bp.add_url_rule(
    "/pedidos", "listar_todos_pedidos", admin_required(controller.listar_todos_pedidos), methods=["GET"]
)
pedido_bp.add_url_rule(
    "/pedidos/usuario/<int:usuario_id>", "listar_pedidos_usuario",
    owner_or_admin("usuario_id")(controller.listar_pedidos_usuario), methods=["GET"],
)
pedido_bp.add_url_rule(
    "/pedidos/<int:pedido_id>/status", "atualizar_status_pedido",
    admin_required(controller.atualizar_status_pedido), methods=["PUT"],
)
