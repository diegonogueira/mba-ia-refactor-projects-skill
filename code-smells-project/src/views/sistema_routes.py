from flask import Blueprint

from src.controllers import sistema_controller as controller
from src.middlewares.admin_guard import admin_only

sistema_bp = Blueprint("sistema", __name__)

sistema_bp.add_url_rule("/", "index", controller.index, methods=["GET"])
sistema_bp.add_url_rule("/health", "health_check", controller.health_check, methods=["GET"])
sistema_bp.add_url_rule("/admin/reset-db", "reset_database", admin_only(controller.reset_database), methods=["POST"])
sistema_bp.add_url_rule("/admin/query", "executar_query", admin_only(controller.executar_query), methods=["POST"])
