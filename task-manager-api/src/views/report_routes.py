"""Rotas de relatórios: apenas URL + método → controller."""
from flask import Blueprint


def build_report_blueprint(controller) -> Blueprint:
    blueprint = Blueprint('reports', __name__)
    blueprint.add_url_rule('/reports/summary', 'summary', controller.summary, methods=['GET'])
    blueprint.add_url_rule('/reports/user/<int:user_id>', 'user_report', controller.user_report, methods=['GET'])
    return blueprint
