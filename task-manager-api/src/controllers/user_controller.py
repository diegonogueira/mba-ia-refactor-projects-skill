import logging

from flask import jsonify, request

from src.controllers.lookups import find_user_or_404
from src.controllers.validators import (
    require_json_object,
    validate_credentials,
    validate_new_user,
    validate_user_changes,
)
from src.models import Task, User
from src.services.auth_service import AuthService
from src.utils.dates import utc_now
from src.views.serializers import (
    serialize_login,
    serialize_user,
    serialize_user_detail,
    serialize_user_listing,
    serialize_user_task,
)

logger = logging.getLogger(__name__)


class UserController:
    def __init__(self, auth_service: AuthService):
        self._auth = auth_service

    def list_users(self):
        counts_by_user = Task.count_by_user()
        users = [serialize_user_listing(user, counts_by_user.get(user.id, (0, 0))[0]) for user in User.list_all()]
        return jsonify(users), 200

    def get_user(self, user_id: int):
        user = find_user_or_404(user_id)
        return jsonify(serialize_user_detail(user, Task.list_by_user(user.id))), 200

    def create_user(self):
        payload = require_json_object(request.get_json(silent=True))
        user = User.create(validate_new_user(payload, email_taken=User.email_taken), "Erro ao criar usuário")
        logger.info("Usuário criado: id=%s", user.id)
        return jsonify(serialize_user(user)), 201

    def update_user(self, user_id: int):
        user = find_user_or_404(user_id)
        payload = require_json_object(request.get_json(silent=True))
        user.update(validate_user_changes(payload, user.id, email_taken=User.email_taken), "Erro ao atualizar")
        return jsonify(serialize_user(user)), 200

    def delete_user(self, user_id: int):
        find_user_or_404(user_id).delete("Erro ao deletar")
        logger.info("Usuário deletado: id=%s", user_id)
        return jsonify({"message": "Usuário deletado com sucesso"}), 200

    def list_user_tasks(self, user_id: int):
        user = find_user_or_404(user_id)
        now = utc_now()
        return jsonify([serialize_user_task(task, now) for task in Task.list_by_user(user.id)]), 200

    def login(self):
        email, password = validate_credentials(require_json_object(request.get_json(silent=True)))
        user = self._auth.authenticate(email, password)
        return jsonify(serialize_login(user, self._auth.issue_token(user))), 200
