import logging

from flask import jsonify, request

from src.controllers.lookups import find_task_or_404
from src.controllers.validators import (
    require_json_object,
    validate_new_task,
    validate_search_filters,
    validate_task_changes,
)
from src.models import Category, Task, User
from src.services.report_service import ReportService
from src.utils.dates import utc_now
from src.views.serializers import serialize_task, serialize_task_detail, serialize_task_listing

logger = logging.getLogger(__name__)


class TaskController:
    def __init__(self, report_service: ReportService):
        self._reports = report_service

    def list_tasks(self):
        now = utc_now()
        return jsonify([serialize_task_listing(task, now) for task in Task.list_with_relations()]), 200

    def get_task(self, task_id: int):
        return jsonify(serialize_task_detail(find_task_or_404(task_id), utc_now())), 200

    def create_task(self):
        payload = require_json_object(request.get_json(silent=True))
        fields = validate_new_task(payload, user_exists=User.exists, category_exists=Category.exists)
        task = Task.create(fields, "Erro ao criar task")
        logger.info("Task criada: id=%s", task.id)
        return jsonify(serialize_task(task)), 201

    def update_task(self, task_id: int):
        task = find_task_or_404(task_id)
        payload = require_json_object(request.get_json(silent=True))
        changes = validate_task_changes(payload, user_exists=User.exists, category_exists=Category.exists)
        task.update(changes, "Erro ao atualizar")
        logger.info("Task atualizada: id=%s", task.id)
        return jsonify(serialize_task(task)), 200

    def delete_task(self, task_id: int):
        find_task_or_404(task_id).delete("Erro ao deletar")
        logger.info("Task deletada: id=%s", task_id)
        return jsonify({"message": "Task deletada com sucesso"}), 200

    def search_tasks(self):
        filters = validate_search_filters(request.args)
        return jsonify([serialize_task(task) for task in Task.search(**filters)]), 200

    def task_stats(self):
        return jsonify(self._reports.task_statistics()), 200
