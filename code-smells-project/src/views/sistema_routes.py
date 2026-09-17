from flask import Blueprint


def build_sistema_blueprint(controller) -> Blueprint:
    bp = Blueprint("sistema", __name__)
    bp.add_url_rule("/", "index", controller.index, methods=["GET"])
    bp.add_url_rule("/health", "health_check", controller.health_check, methods=["GET"])
    return bp
