from flask import Blueprint

from src.controllers import relatorio_controller as controller
from src.middlewares.auth_guard import admin_required

relatorio_bp = Blueprint("relatorios", __name__)

relatorio_bp.add_url_rule(
    "/relatorios/vendas", "relatorio_vendas", admin_required(controller.relatorio_vendas), methods=["GET"]
)
