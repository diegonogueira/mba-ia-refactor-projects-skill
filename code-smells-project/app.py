"""Ponto de entrada: `python app.py` sobe a API com as configurações do ambiente."""
import logging

from src.app import create_app
from src.config.settings import load_settings

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    app = create_app(settings)
    logger.info("Servidor iniciado em http://%s:%s", settings.host, settings.port)
    app.run(host=settings.host, port=settings.port, debug=settings.debug)


if __name__ == "__main__":
    main()
