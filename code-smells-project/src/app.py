"""Composition root: cria a aplicação Flask e conecta config, banco, rotas e middlewares."""
from flask import Flask
from flask_cors import CORS

from src.config.settings import load_settings
from src.middlewares.error_handler import register_error_handlers
from src.models.database import init_database
from src.views.pedido_routes import pedido_bp
from src.views.produto_routes import produto_bp
from src.views.relatorio_routes import relatorio_bp
from src.views.sistema_routes import sistema_bp
from src.views.usuario_routes import usuario_bp


def create_app(settings=None):
    settings = settings or load_settings()

    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=settings.secret_key,
        DEBUG=settings.debug,
        DATABASE_PATH=settings.database_path,
        APP_ENV=settings.app_env,
        SEED_DATABASE=settings.seed_database,
        ADMIN_ENDPOINTS_ENABLED=settings.admin_endpoints_enabled,
        ADMIN_TOKEN=settings.admin_token,
    )
    CORS(app, origins=settings.cors_origins)

    for blueprint in (produto_bp, usuario_bp, pedido_bp, relatorio_bp, sistema_bp):
        app.register_blueprint(blueprint)
    register_error_handlers(app)
    init_database(app)
    return app
