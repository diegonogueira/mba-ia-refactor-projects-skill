"""Ponto de entrada da aplicação: mantém `python app.py` funcionando."""
from src.app import create_app
from src.config.settings import load_settings


def main() -> None:
    settings = load_settings()
    app = create_app(settings)
    app.run(host=settings.host, port=settings.port, debug=settings.debug)


if __name__ == '__main__':
    main()
