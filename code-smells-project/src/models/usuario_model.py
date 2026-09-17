import hmac

from werkzeug.security import check_password_hash, generate_password_hash

from src.models.database import transaction
from src.utils.errors import ConflictError

TIPO_PADRAO = "cliente"
_PREFIXOS_HASH = ("scrypt:", "pbkdf2:")


def hash_senha(senha: str) -> str:
    return generate_password_hash(senha)


class UsuarioModel:
    def __init__(self, get_connection):
        self._get_connection = get_connection

    def listar(self) -> list[dict]:
        rows = self._get_connection().execute(
            "SELECT id, nome, email, tipo, criado_em FROM usuarios"
        ).fetchall()
        return [dict(row) for row in rows]

    def buscar_por_id(self, usuario_id: int) -> dict | None:
        row = self._get_connection().execute(
            "SELECT id, nome, email, tipo, criado_em FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()
        return dict(row) if row else None

    def existe(self, usuario_id: int) -> bool:
        row = self._get_connection().execute("SELECT 1 FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        return row is not None

    def criar(self, nome: str, email: str, senha: str, tipo: str = TIPO_PADRAO) -> int:
        conn = self._get_connection()
        with transaction(conn):
            if conn.execute("SELECT 1 FROM usuarios WHERE email = ? LIMIT 1", (email,)).fetchone():
                raise ConflictError("Email já cadastrado")
            cursor = conn.execute(
                "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                (nome, email, hash_senha(senha), tipo),
            )
        return cursor.lastrowid

    def autenticar(self, email: str, senha: str) -> dict | None:
        rows = self._get_connection().execute(
            "SELECT id, nome, email, senha, tipo FROM usuarios WHERE email = ? ORDER BY id", (email,)
        ).fetchall()
        for row in rows:
            if self._senha_confere(row, senha):
                return {"id": row["id"], "nome": row["nome"], "email": row["email"], "tipo": row["tipo"]}
        return None

    def _senha_confere(self, row, senha: str) -> bool:
        armazenada = row["senha"] or ""
        if armazenada.startswith(_PREFIXOS_HASH):
            return check_password_hash(armazenada, senha)
        # Senha legada em texto puro (bancos criados pela versão anterior): confere e migra para hash.
        if hmac.compare_digest(armazenada.encode(), senha.encode()):
            self._get_connection().execute(
                "UPDATE usuarios SET senha = ? WHERE id = ?", (hash_senha(senha), row["id"])
            )
            return True
        return False
