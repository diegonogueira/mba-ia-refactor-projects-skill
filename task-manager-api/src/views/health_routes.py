from flask import Blueprint

from src.controllers.health_controller import HealthController


def build_health_blueprint(controller: HealthController) -> Blueprint:
    blueprint = Blueprint("health", __name__)
    blueprint.add_url_rule("/health", "health", controller.health, methods=["GET"])
    blueprint.add_url_rule("/", "index", controller.index, methods=["GET"])
    return blueprint
