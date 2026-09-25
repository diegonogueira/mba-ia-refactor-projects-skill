from flask import Blueprint

from src.controllers import usuario_controller as controller
from src.middlewares.auth_guard import admin_required, owner_or_admin

usuario_bp = Blueprint("usuarios", __name__)

usuario_bp.add_url_rule("/usuarios", "listar_usuarios", admin_required(controller.listar_usuarios), methods=["GET"])
usuario_bp.add_url_rule(
    "/usuarios/<int:usuario_id>", "buscar_usuario", owner_or_admin("usuario_id")(controller.buscar_usuario),
    methods=["GET"],
)
usuario_bp.add_url_rule("/usuarios", "criar_usuario", controller.criar_usuario, methods=["POST"])
usuario_bp.add_url_rule("/login", "login", controller.login, methods=["POST"])
