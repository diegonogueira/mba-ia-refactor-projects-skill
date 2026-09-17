"""Script para popular o banco com dados iniciais: python seed.py"""
from src.app import create_app
from src.models.seed import seed_database


def main() -> None:
    app = create_app()
    with app.app_context():
        counts = seed_database()
    print('Seed concluído com sucesso!')
    print(f"  {counts['users']} usuários")
    print(f"  {counts['categories']} categorias")
    print(f"  {counts['tasks']} tasks")


if __name__ == '__main__':
    main()
