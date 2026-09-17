from flask import Blueprint


def build_usuario_blueprint(controller) -> Blueprint:
    bp = Blueprint("usuarios", __name__)
    bp.add_url_rule("/usuarios", "listar_usuarios", controller.listar_usuarios, methods=["GET"])
    bp.add_url_rule("/usuarios/<int:usuario_id>", "buscar_usuario", controller.buscar_usuario, methods=["GET"])
    bp.add_url_rule("/usuarios", "criar_usuario", controller.criar_usuario, methods=["POST"])
    bp.add_url_rule("/login", "login", controller.login, methods=["POST"])
    return bp
