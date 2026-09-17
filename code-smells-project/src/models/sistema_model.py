class SistemaModel:
    def __init__(self, get_connection):
        self._get_connection = get_connection

    def contagens(self) -> dict:
        row = self._get_connection().execute(
            """
            SELECT (SELECT COUNT(*) FROM produtos) AS produtos,
                   (SELECT COUNT(*) FROM usuarios) AS usuarios,
                   (SELECT COUNT(*) FROM pedidos) AS pedidos
            """
        ).fetchone()
        return dict(row)
