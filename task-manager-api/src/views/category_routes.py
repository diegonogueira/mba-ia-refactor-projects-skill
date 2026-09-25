"""Rotas de categorias: apenas URL + método (+ guard) → controller.

A listagem é pública; o catálogo de categorias é compartilhado e só um admin o altera.
"""
from flask import Blueprint


def build_category_blueprint(controller, auth) -> Blueprint:
    blueprint = Blueprint('categories', __name__)
    blueprint.add_url_rule('/categories', 'list_categories', controller.list_categories, methods=['GET'])
    blueprint.add_url_rule('/categories', 'create_category', auth.admin_required(controller.create_category),
                           methods=['POST'])
    blueprint.add_url_rule('/categories/<int:category_id>', 'update_category',
                           auth.admin_required(controller.update_category), methods=['PUT'])
    blueprint.add_url_rule('/categories/<int:category_id>', 'delete_category',
                           auth.admin_required(controller.delete_category), methods=['DELETE'])
    return blueprint
