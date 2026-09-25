"""Rotas de relatórios: apenas URL + método (+ guard) → controller."""
from flask import Blueprint


def build_report_blueprint(controller, auth) -> Blueprint:
    blueprint = Blueprint('reports', __name__)
    blueprint.add_url_rule('/reports/summary', 'summary', auth.admin_required(controller.summary), methods=['GET'])
    blueprint.add_url_rule('/reports/user/<int:user_id>', 'user_report',
                           auth.owner_or_admin('user_id')(controller.user_report), methods=['GET'])
    return blueprint
