from flask import Blueprint


def build_relatorio_blueprint(controller) -> Blueprint:
    bp = Blueprint("relatorios", __name__)
    bp.add_url_rule("/relatorios/vendas", "relatorio_vendas", controller.relatorio_vendas, methods=["GET"])
    return bp
