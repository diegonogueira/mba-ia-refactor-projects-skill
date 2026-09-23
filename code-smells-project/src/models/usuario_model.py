"""Acesso a dados e regras da entidade usuário."""
import hmac

from werkzeug.security import check_password_hash, generate_password_hash

from src.models.database import get_connection, transaction
from src.utils.errors import ConflictError

TIPO_PADRAO = "cliente"
TIPO_ADMIN = "admin"
PREFIXOS_HASH = ("scrypt:", "pbkdf2:")

COLUNAS_PUBLICAS = "id, nome, email, tipo, criado_em"


def listar_todos():
    linhas = get_connection().execute(f"SELECT {COLUNAS_PUBLICAS} FROM usuarios").fetchall()
    return [dict(linha) for linha in linhas]


def buscar_por_id(usuario_id):
    linha = get_connection().execute(
        f"SELECT {COLUNAS_PUBLICAS} FROM usuarios WHERE id = ?", (usuario_id,)
    ).fetchone()
    return dict(linha) if linha else None


def criar(nome, email, senha):
    with transaction(immediate=True) as conexao:
        if conexao.execute("SELECT 1 FROM usuarios WHERE email = ?", (email,)).fetchone():
            raise ConflictError("Email já cadastrado")
        cursor = conexao.execute(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            (nome, email, generate_password_hash(senha), TIPO_PADRAO),
        )
    return cursor.lastrowid


def autenticar(email, senha):
    """Retorna o usuário quando as credenciais conferem; senhas legadas em texto puro são migradas para hash."""
    linha = get_connection().execute(
        f"SELECT {COLUNAS_PUBLICAS}, senha FROM usuarios WHERE email = ?", (email,)
    ).fetchone()
    if linha is None:
        return None

    senha_armazenada = linha["senha"] or ""
    if senha_armazenada.startswith(PREFIXOS_HASH):
        if not check_password_hash(senha_armazenada, senha):
            return None
    elif hmac.compare_digest(senha_armazenada.encode(), senha.encode()):
        with transaction() as conexao:
            conexao.execute(
                "UPDATE usuarios SET senha = ? WHERE id = ?", (generate_password_hash(senha), linha["id"])
            )
    else:
        return None

    usuario = dict(linha)
    del usuario["senha"]
    return usuario
