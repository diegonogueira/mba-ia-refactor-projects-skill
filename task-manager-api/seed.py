"""Script para popular o banco com dados iniciais: python seed.py"""
from src.app import create_app
from src.models.seed import SEED_PASSWORD_VARIABLE, seed_database


def main() -> None:
    app = create_app()
    with app.app_context():
        result = seed_database()
    print('Seed concluído com sucesso!')
    print(f"  {result['users']} usuários")
    print(f"  {result['categories']} categorias")
    print(f"  {result['tasks']} tasks")
    if result['password_generated']:
        print(f"\nSenha sorteada para os usuários de exemplo: {result['password']}")
        print(f"Ela não fica gravada em lugar nenhum — anote agora ou defina {SEED_PASSWORD_VARIABLE}"
              ' antes de rodar o seed.')


if __name__ == '__main__':
    main()
