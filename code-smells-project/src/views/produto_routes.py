from flask import Blueprint


def build_produto_blueprint(controller) -> Blueprint:
    bp = Blueprint("produtos", __name__)
    bp.add_url_rule("/produtos", "listar_produtos", controller.listar_produtos, methods=["GET"])
    bp.add_url_rule("/produtos/busca", "buscar_produtos", controller.buscar_produtos, methods=["GET"])
    bp.add_url_rule("/produtos/<int:produto_id>", "buscar_produto", controller.buscar_produto, methods=["GET"])
    bp.add_url_rule("/produtos", "criar_produto", controller.criar_produto, methods=["POST"])
    bp.add_url_rule("/produtos/<int:produto_id>", "atualizar_produto", controller.atualizar_produto, methods=["PUT"])
    bp.add_url_rule("/produtos/<int:produto_id>", "deletar_produto", controller.deletar_produto, methods=["DELETE"])
    return bp
