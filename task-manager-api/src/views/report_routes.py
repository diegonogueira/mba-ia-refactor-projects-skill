from flask import Blueprint

from src.controllers.report_controller import ReportController


def build_report_blueprint(controller: ReportController) -> Blueprint:
    blueprint = Blueprint("reports", __name__)
    blueprint.add_url_rule("/reports/summary", "summary", controller.summary, methods=["GET"])
    blueprint.add_url_rule("/reports/user/<int:user_id>", "user_report", controller.user_report, methods=["GET"])
    return blueprint
