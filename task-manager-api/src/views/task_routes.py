"""Rotas de tasks: apenas URL + método (+ guard) → controller.

Leituras são públicas; escritas exigem login e o controller confere o dono da task.
"""
from flask import Blueprint


def build_task_blueprint(controller, auth) -> Blueprint:
    blueprint = Blueprint('tasks', __name__)
    blueprint.add_url_rule('/tasks', 'list_tasks', controller.list_tasks, methods=['GET'])
    blueprint.add_url_rule('/tasks', 'create_task', auth.authenticated(controller.create_task), methods=['POST'])
    blueprint.add_url_rule('/tasks/search', 'search_tasks', controller.search_tasks, methods=['GET'])
    blueprint.add_url_rule('/tasks/stats', 'task_stats', controller.task_stats, methods=['GET'])
    blueprint.add_url_rule('/tasks/<int:task_id>', 'get_task', controller.get_task, methods=['GET'])
    blueprint.add_url_rule('/tasks/<int:task_id>', 'update_task', auth.authenticated(controller.update_task),
                           methods=['PUT'])
    blueprint.add_url_rule('/tasks/<int:task_id>', 'delete_task', auth.authenticated(controller.delete_task),
                           methods=['DELETE'])
    return blueprint
