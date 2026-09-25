"""Rotas de usuários e login: apenas URL + método (+ guard) → controller.

Cadastro e login são públicos; a listagem é de admin; os dados de um usuário, do próprio ou de admin.
"""
from flask import Blueprint

from src.middlewares.admin_guard import admin_only


def build_user_blueprint(controller, auth) -> Blueprint:
    owner_or_admin = auth.owner_or_admin('user_id')
    blueprint = Blueprint('users', __name__)
    blueprint.add_url_rule('/users', 'list_users', auth.admin_required(controller.list_users), methods=['GET'])
    blueprint.add_url_rule('/users', 'create_user', controller.create_user, methods=['POST'])
    blueprint.add_url_rule('/users/<int:user_id>', 'get_user', owner_or_admin(controller.get_user), methods=['GET'])
    blueprint.add_url_rule('/users/<int:user_id>', 'update_user', owner_or_admin(controller.update_user),
                           methods=['PUT'])
    # apagar um usuário remove em cascata todas as tasks dele: só com o guard administrativo
    blueprint.add_url_rule('/users/<int:user_id>', 'delete_user', admin_only(controller.delete_user),
                           methods=['DELETE'])
    blueprint.add_url_rule('/users/<int:user_id>/tasks', 'list_user_tasks', owner_or_admin(controller.list_user_tasks),
                           methods=['GET'])
    blueprint.add_url_rule('/login', 'login', controller.login, methods=['POST'])
    return blueprint
