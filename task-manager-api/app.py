"""Entry point: `python app.py` (WSGI servers can use `app:app`)."""
from src.app import create_app
from src.config.settings import load_settings

settings = load_settings()
app = create_app(settings)

if __name__ == "__main__":
    app.run(host=settings.host, port=settings.port, debug=settings.debug)
