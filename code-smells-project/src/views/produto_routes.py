from flask import Blueprint

from src.controllers import produto_controller as controller
from src.middlewares.auth_guard import admin_required

produto_bp = Blueprint("produtos", __name__)

# Vitrine: leituras públicas.
produto_bp.add_url_rule("/produtos", "listar_produtos", controller.listar_produtos, methods=["GET"])
produto_bp.add_url_rule("/produtos/busca", "buscar_produtos", controller.buscar_produtos, methods=["GET"])
produto_bp.add_url_rule("/produtos/<int:produto_id>", "buscar_produto", controller.buscar_produto, methods=["GET"])

# Gestão do catálogo: somente administradores.
produto_bp.add_url_rule("/produtos", "criar_produto", admin_required(controller.criar_produto), methods=["POST"])
produto_bp.add_url_rule(
    "/produtos/<int:produto_id>", "atualizar_produto", admin_required(controller.atualizar_produto), methods=["PUT"]
)
produto_bp.add_url_rule(
    "/produtos/<int:produto_id>", "deletar_produto", admin_required(controller.deletar_produto), methods=["DELETE"]
)
