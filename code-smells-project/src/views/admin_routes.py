from flask import Blueprint

from src.middlewares.admin_guard import admin_only


def build_admin_blueprint(controller) -> Blueprint:
    bp = Blueprint("admin", __name__)
    bp.add_url_rule("/admin/reset-db", "reset_database", admin_only(controller.reset_database), methods=["POST"])
    bp.add_url_rule("/admin/query", "executar_query", admin_only(controller.executar_query), methods=["POST"])
    return bp
