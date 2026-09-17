from flask import jsonify

from src.controllers.lookups import find_user_or_404
from src.services.report_service import ReportService
from src.views.serializers import serialize_user_report


class ReportController:
    def __init__(self, report_service: ReportService):
        self._reports = report_service

    def summary(self):
        return jsonify(self._reports.summary()), 200

    def user_report(self, user_id: int):
        user = find_user_or_404(user_id)
        return jsonify(serialize_user_report(user, self._reports.user_statistics(user))), 200
