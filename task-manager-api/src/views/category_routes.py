"""Rotas de categorias: apenas URL + método → controller."""
from flask import Blueprint


def build_category_blueprint(controller) -> Blueprint:
    blueprint = Blueprint('categories', __name__)
    blueprint.add_url_rule('/categories', 'list_categories', controller.list_categories, methods=['GET'])
    blueprint.add_url_rule('/categories', 'create_category', controller.create_category, methods=['POST'])
    blueprint.add_url_rule('/categories/<int:category_id>', 'update_category', controller.update_category,
                           methods=['PUT'])
    blueprint.add_url_rule('/categories/<int:category_id>', 'delete_category', controller.delete_category,
                           methods=['DELETE'])
    return blueprint
