"""Composition root: cria a aplicação e liga config, models, services, controllers, views e middlewares."""
from flask import Flask
from flask_cors import CORS

from src.config.logging_config import configure_logging
from src.config.settings import Settings, load_settings
from src.controllers.admin_controller import AdminController
from src.controllers.pedido_controller import PedidoController
from src.controllers.produto_controller import ProdutoController
from src.controllers.relatorio_controller import RelatorioController
from src.controllers.sistema_controller import SistemaController
from src.controllers.usuario_controller import UsuarioController
from src.middlewares.error_handler import register_error_handlers
from src.models.admin_model import AdminModel
from src.models.database import get_connection, get_read_only_connection, init_database
from src.models.pedido_model import PedidoModel
from src.models.produto_model import ProdutoModel
from src.models.relatorio_model import RelatorioModel
from src.models.seed import seed_database
from src.models.sistema_model import SistemaModel
from src.models.usuario_model import UsuarioModel
from src.services.notification_service import NotificationService
from src.services.pedido_service import PedidoService
from src.views.admin_routes import build_admin_blueprint
from src.views.pedido_routes import build_pedido_blueprint
from src.views.produto_routes import build_produto_blueprint
from src.views.relatorio_routes import build_relatorio_blueprint
from src.views.sistema_routes import build_sistema_blueprint
from src.views.usuario_routes import build_usuario_blueprint


def create_app(settings: Settings | None = None) -> Flask:
    configure_logging()
    settings = settings or load_settings()

    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=settings.secret_key,
        DEBUG=settings.debug,
        DATABASE_PATH=settings.database_path,
        ADMIN_ENDPOINTS_ENABLED=settings.admin_endpoints_enabled,
        ADMIN_TOKEN=settings.admin_token,
    )
    CORS(app, origins=settings.cors_origins)
    init_database(app, seed=seed_database if settings.seed_database else None)

    produto_model = ProdutoModel(get_connection)
    usuario_model = UsuarioModel(get_connection)
    pedido_model = PedidoModel(get_connection)
    pedido_service = PedidoService(pedido_model, usuario_model, NotificationService())

    blueprints = (
        build_sistema_blueprint(SistemaController(SistemaModel(get_connection), settings.app_env)),
        build_produto_blueprint(ProdutoController(produto_model)),
        build_usuario_blueprint(UsuarioController(usuario_model)),
        build_pedido_blueprint(PedidoController(pedido_service, pedido_model)),
        build_relatorio_blueprint(RelatorioController(RelatorioModel(get_connection))),
        build_admin_blueprint(AdminController(AdminModel(get_connection, get_read_only_connection))),
    )
    for blueprint in blueprints:
        app.register_blueprint(blueprint)

    register_error_handlers(app)
    return app
