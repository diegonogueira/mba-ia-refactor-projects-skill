"""Dados de demonstração inseridos quando o banco está vazio (desative com SEED_DATABASE=false)."""
from src.models.database import transaction
from src.models.usuario_model import hash_senha

PRODUTOS_EXEMPLO = [
    ("Notebook Gamer", "Notebook potente para jogos", 5999.99, 10, "informatica"),
    ("Mouse Wireless", "Mouse sem fio ergonômico", 89.90, 50, "informatica"),
    ("Teclado Mecânico", "Teclado mecânico RGB", 299.90, 30, "informatica"),
    ("Monitor 27''", "Monitor 27 polegadas 144hz", 1899.90, 15, "informatica"),
    ("Headset Gamer", "Headset com microfone", 199.90, 25, "informatica"),
    ("Cadeira Gamer", "Cadeira ergonômica", 1299.90, 8, "moveis"),
    ("Webcam HD", "Webcam 1080p", 249.90, 20, "informatica"),
    ("Hub USB", "Hub USB 3.0 7 portas", 79.90, 40, "informatica"),
    ("SSD 1TB", "SSD NVMe 1TB", 449.90, 35, "informatica"),
    ("Camiseta Dev", "Camiseta estampa código", 59.90, 100, "vestuario"),
]

# Contas de demonstração: as senhas são gravadas com hash, mas são conhecidas — não use em produção.
USUARIOS_EXEMPLO = [
    ("Admin", "admin@loja.com", "admin123", "admin"),
    ("João Silva", "joao@email.com", "123456", "cliente"),
    ("Maria Santos", "maria@email.com", "senha123", "cliente"),
]


def seed_database(conn) -> None:
    if conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] > 0:
        return
    with transaction(conn):
        conn.executemany(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
            PRODUTOS_EXEMPLO,
        )
        for nome, email, senha, tipo in USUARIOS_EXEMPLO:
            conn.execute(
                "INSERT INTO usuarios (nome, email, senha, tipo) "
                "SELECT ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE email = ?)",
                (nome, email, hash_senha(senha), tipo, email),
            )
