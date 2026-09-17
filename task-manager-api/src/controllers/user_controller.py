"""Controller de usuários e login."""
import logging

from flask import jsonify, request

from src.controllers.validators.user_validator import (validate_credentials, validate_new_user,
                                                       validate_user_changes)
from src.models.task_model import NO_TASKS, Task
from src.models.user_model import User
from src.utils.datetime_utils import utcnow_naive
from src.utils.errors import NotFoundError
from src.views.serializers import (serialize_login, serialize_user, serialize_user_task,
                                   serialize_user_with_task_count, serialize_user_with_tasks)

logger = logging.getLogger(__name__)

USER_NOT_FOUND_MESSAGE = 'Usuário não encontrado'
USER_DELETED_MESSAGE = 'Usuário deletado com sucesso'


class UserController:
    def __init__(self, auth_service):
        self._auth = auth_service

    def list_users(self):
        counts = Task.count_by_user()
        return jsonify([serialize_user_with_task_count(user, counts.get(user.id, NO_TASKS).total)
                        for user in User.list_all()]), 200

    def get_user(self, user_id):
        user = self._find(user_id)
        return jsonify(serialize_user_with_tasks(user, Task.list_by_user(user_id))), 200

    def create_user(self):
        fields = validate_new_user(request.get_json(silent=True), email_in_use=User.email_in_use)
        user = User.register(**fields)
        logger.info('Usuário criado: id=%s', user.id)
        return jsonify(serialize_user(user)), 201

    def update_user(self, user_id):
        user = self._find(user_id)
        changes = validate_user_changes(
            request.get_json(silent=True),
            email_in_use=lambda email: User.email_in_use(email, exclude_id=user_id),
        )
        user.assign(changes)
        user.update()
        return jsonify(serialize_user(user)), 200

    def delete_user(self, user_id):
        self._find(user_id).delete()
        logger.info('Usuário deletado: id=%s', user_id)
        return jsonify({'message': USER_DELETED_MESSAGE}), 200

    def list_user_tasks(self, user_id):
        self._find(user_id)
        now = utcnow_naive()
        return jsonify([serialize_user_task(task, now) for task in Task.list_by_user(user_id)]), 200

    def login(self):
        email, password = validate_credentials(request.get_json(silent=True))
        user = self._auth.authenticate(email, password)
        return jsonify(serialize_login(user, self._auth.issue_token(user))), 200

    @staticmethod
    def _find(user_id) -> User:
        user = User.get_by_id(user_id)
        if user is None:
            raise NotFoundError(USER_NOT_FOUND_MESSAGE)
        return user
