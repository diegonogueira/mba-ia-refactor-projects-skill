"""Controller de tasks: lê a requisição, valida, chama os modelos e escolhe status e view."""
import logging

from flask import jsonify, request

from src.controllers.validators.task_validator import (parse_search_filters, validate_new_task,
                                                       validate_task_changes)
from src.models.category_model import Category
from src.models.task_model import Task
from src.models.user_model import User
from src.utils.datetime_utils import utcnow_naive
from src.utils.errors import NotFoundError
from src.views.serializers import (serialize_task, serialize_task_detail, serialize_task_statistics,
                                   serialize_task_with_relations)

logger = logging.getLogger(__name__)

TASK_NOT_FOUND_MESSAGE = 'Task não encontrada'
TASK_DELETED_MESSAGE = 'Task deletada com sucesso'


class TaskController:
    def __init__(self, report_service):
        self._reports = report_service

    def list_tasks(self):
        now = utcnow_naive()
        tasks = Task.list_all(with_relations=True)
        return jsonify([serialize_task_with_relations(task, now) for task in tasks]), 200

    def get_task(self, task_id):
        return jsonify(serialize_task_detail(self._find(task_id))), 200

    def create_task(self):
        fields = validate_new_task(request.get_json(silent=True),
                                   user_exists=User.exists, category_exists=Category.exists)
        task = Task()
        task.assign(fields)
        task.create()
        logger.info('Task criada: id=%s', task.id)
        return jsonify(serialize_task(task)), 201

    def update_task(self, task_id):
        task = self._find(task_id)
        changes = validate_task_changes(request.get_json(silent=True),
                                        user_exists=User.exists, category_exists=Category.exists)
        task.assign(changes)
        task.update()
        logger.info('Task atualizada: id=%s', task.id)
        return jsonify(serialize_task(task)), 200

    def delete_task(self, task_id):
        self._find(task_id).delete()
        logger.info('Task deletada: id=%s', task_id)
        return jsonify({'message': TASK_DELETED_MESSAGE}), 200

    def search_tasks(self):
        filters = parse_search_filters(request.args)
        return jsonify([serialize_task(task) for task in Task.search(**filters)]), 200

    def task_stats(self):
        return jsonify(serialize_task_statistics(self._reports.task_statistics())), 200

    @staticmethod
    def _find(task_id) -> Task:
        task = Task.get_by_id(task_id)
        if task is None:
            raise NotFoundError(TASK_NOT_FOUND_MESSAGE)
        return task
