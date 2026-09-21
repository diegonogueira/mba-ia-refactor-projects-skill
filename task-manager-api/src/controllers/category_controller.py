"""Controller de categorias."""
import logging

from flask import jsonify, request

from src.controllers.validators.category_validator import (validate_category_changes,
                                                           validate_new_category)
from src.models.category_model import CATEGORY_NOT_FOUND_MESSAGE, Category
from src.models.task_model import Task
from src.utils.errors import NotFoundError
from src.views.serializers import serialize_category

logger = logging.getLogger(__name__)

CATEGORY_DELETED_MESSAGE = 'Categoria deletada'


class CategoryController:
    def list_categories(self):
        counts = Task.count_by_category()
        return jsonify([serialize_category(category, task_count=counts.get(category.id, 0))
                        for category in Category.list_all()]), 200

    def create_category(self):
        category = Category()
        category.assign(validate_new_category(request.get_json(silent=True)))
        category.create()
        logger.info('Categoria criada: id=%s', category.id)
        return jsonify(serialize_category(category)), 201

    def update_category(self, category_id):
        category = self._find(category_id)
        category.assign(validate_category_changes(request.get_json(silent=True)))
        category.update()
        return jsonify(serialize_category(category)), 200

    def delete_category(self, category_id):
        self._find(category_id).delete()
        logger.info('Categoria deletada: id=%s', category_id)
        return jsonify({'message': CATEGORY_DELETED_MESSAGE}), 200

    @staticmethod
    def _find(category_id) -> Category:
        category = Category.get_by_id(category_id)
        if category is None:
            raise NotFoundError(CATEGORY_NOT_FOUND_MESSAGE)
        return category
