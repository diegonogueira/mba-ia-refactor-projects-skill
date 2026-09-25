"""Conexão SQLite por contexto de aplicação, transações, schema e seed."""
import logging
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from flask import current_app, g
from werkzeug.security import generate_password_hash

from src.models.status_pedido import STATUS_PENDENTE
from src.models.tipos_usuario import TIPO_ADMIN, TIPO_CLIENTE

logger = logging.getLogger(__name__)

DatabaseError = sqlite3.Error

# Bytes de entropia da senha gerada para os usuários de demonstração quando SEED_PASSWORD não é definido.
SEED_PASSWORD_BYTES = 16

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    descricao TEXT,
    preco REAL,
    estoque INTEGER,
    categoria TEXT,
    ativo INTEGER DEFAULT 1,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    email TEXT,
    senha TEXT,
    tipo TEXT DEFAULT '{TIPO_CLIENTE}',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS pedidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER REFERENCES usuarios (id),
    status TEXT DEFAULT '{STATUS_PENDENTE}',
    total REAL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS itens_pedido (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER REFERENCES pedidos (id),
    produto_id INTEGER REFERENCES produtos (id),
    quantidade INTEGER,
    preco_unitario REAL
);
"""

PRODUTOS_SEED = [
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

# Usuários de demonstração (desative com SEED_DATABASE=false). A senha NÃO fica no código:
# vem de SEED_PASSWORD ou é sorteada no primeiro boot e registrada no log uma única vez.
USUARIOS_SEED = [
    ("Admin", "admin@loja.com", TIPO_ADMIN),
    ("João Silva", "joao@email.com", TIPO_CLIENTE),
    ("Maria Santos", "maria@email.com", TIPO_CLIENTE),
]


def get_connection():
    if "db" not in g:
        conexao = sqlite3.connect(current_app.config["DATABASE_PATH"])
        conexao.row_factory = sqlite3.Row
        conexao.execute("PRAGMA foreign_keys = ON")
        g.db = conexao
    return g.db


def get_read_only_connection():
    caminho = Path(current_app.config["DATABASE_PATH"]).resolve()
    conexao = sqlite3.connect(f"{caminho.as_uri()}?mode=ro", uri=True)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA query_only = ON")
    return conexao


def close_connection(_erro=None):
    conexao = g.pop("db", None)
    if conexao is not None:
        conexao.close()


@contextmanager
def transaction(immediate=False):
    """Executa o bloco numa transação: commit no sucesso, rollback em qualquer exceção."""
    conexao = get_connection()
    conexao.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
    try:
        yield conexao
    except BaseException:
        conexao.rollback()
        raise
    conexao.commit()


def _senha_do_seed():
    """Senha dos usuários de demonstração: de SEED_PASSWORD ou sorteada e exibida uma única vez."""
    senha = current_app.config["SEED_PASSWORD"]
    if senha:
        return senha
    senha = secrets.token_urlsafe(SEED_PASSWORD_BYTES)
    logger.warning(
        "SEED_PASSWORD não definido; usuários de demonstração criados com a senha %s "
        "(exibida apenas agora — defina SEED_PASSWORD para escolher a sua ou SEED_DATABASE=false para não criá-los)",
        senha,
    )
    return senha


def _seed(conexao):
    if conexao.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] > 0:
        return
    senha_hash = generate_password_hash(_senha_do_seed())
    with transaction() as transacao:
        transacao.executemany(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
            PRODUTOS_SEED,
        )
        transacao.executemany(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            [(nome, email, senha_hash, tipo) for nome, email, tipo in USUARIOS_SEED],
        )


def init_database(app):
    app.teardown_appcontext(close_connection)
    with app.app_context():
        conexao = get_connection()
        conexao.executescript(SCHEMA)
        if app.config["SEED_DATABASE"]:
            _seed(conexao)
