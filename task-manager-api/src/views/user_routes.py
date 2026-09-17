from flask import Blueprint

from src.controllers.user_controller import UserController


def build_user_blueprint(controller: UserController) -> Blueprint:
    blueprint = Blueprint("users", __name__)
    blueprint.add_url_rule("/users", "list_users", controller.list_users, methods=["GET"])
    blueprint.add_url_rule("/users/<int:user_id>", "get_user", controller.get_user, methods=["GET"])
    blueprint.add_url_rule("/users", "create_user", controller.create_user, methods=["POST"])
    blueprint.add_url_rule("/users/<int:user_id>", "update_user", controller.update_user, methods=["PUT"])
    blueprint.add_url_rule("/users/<int:user_id>", "delete_user", controller.delete_user, methods=["DELETE"])
    blueprint.add_url_rule("/users/<int:user_id>/tasks", "list_user_tasks", controller.list_user_tasks, methods=["GET"])
    blueprint.add_url_rule("/login", "login", controller.login, methods=["POST"])
    return blueprint
