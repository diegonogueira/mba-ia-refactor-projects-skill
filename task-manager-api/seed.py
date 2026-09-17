"""Script para popular o banco com dados iniciais"""
from src.app import create_app
from src.models.seed import seed_database


def main() -> None:
    app = create_app()
    with app.app_context():
        totals = seed_database()
    print("Seed concluído com sucesso!")
    print(f"  {totals['users']} usuários")
    print(f"  {totals['categories']} categorias")
    print(f"  {totals['tasks']} tasks")


if __name__ == "__main__":
    main()
