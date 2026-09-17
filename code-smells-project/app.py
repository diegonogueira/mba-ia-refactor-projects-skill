"""Entry point: mantém `python app.py` funcionando; a montagem da aplicação fica em src/app.py."""
import logging

from src.app import create_app
from src.config.logging_config import configure_logging
from src.config.settings import load_settings

configure_logging()
settings = load_settings()
app = create_app(settings)

if __name__ == "__main__":
    logging.getLogger(__name__).info("Servidor iniciado em http://%s:%s", settings.host, settings.port)
    app.run(host=settings.host, port=settings.port, debug=settings.debug)
