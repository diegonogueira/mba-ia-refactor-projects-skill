"""Rotas de raiz e health check: apenas URL + método → controller."""
from flask import Blueprint


def build_health_blueprint(controller) -> Blueprint:
    blueprint = Blueprint('health', __name__)
    blueprint.add_url_rule('/', 'index', controller.index, methods=['GET'])
    blueprint.add_url_rule('/health', 'health', controller.health, methods=['GET'])
    return blueprint
