from flask import jsonify, request

from src.controllers.lookups import find_category_or_404
from src.controllers.validators import require_json_object, validate_category_changes, validate_new_category
from src.models import Category, Task
from src.views.serializers import serialize_category, serialize_category_listing


class CategoryController:
    def list_categories(self):
        counts_by_category = Task.count_by_category()
        categories = [
            serialize_category_listing(category, counts_by_category.get(category.id, 0))
            for category in Category.list_all()
        ]
        return jsonify(categories), 200

    def create_category(self):
        payload = require_json_object(request.get_json(silent=True))
        category = Category.create(validate_new_category(payload), "Erro ao criar categoria")
        return jsonify(serialize_category(category)), 201

    def update_category(self, category_id: int):
        category = find_category_or_404(category_id)
        payload = require_json_object(request.get_json(silent=True), allow_empty=True)
        category.update(validate_category_changes(payload), "Erro ao atualizar")
        return jsonify(serialize_category(category)), 200

    def delete_category(self, category_id: int):
        find_category_or_404(category_id).delete("Erro ao deletar")
        return jsonify({"message": "Categoria deletada"}), 200
