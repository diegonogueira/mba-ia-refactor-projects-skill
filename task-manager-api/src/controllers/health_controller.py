"""Controller de disponibilidade e identificação da API."""
from flask import jsonify

from src.utils.datetime_utils import utcnow_naive

API_NAME = 'Task Manager API'
API_VERSION = '1.0'


class HealthController:
    def index(self):
        return jsonify({'message': API_NAME, 'version': API_VERSION}), 200

    def health(self):
        return jsonify({'status': 'ok', 'timestamp': str(utcnow_naive())}), 200
