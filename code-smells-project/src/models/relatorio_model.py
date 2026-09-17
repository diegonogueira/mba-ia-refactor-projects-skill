from src.models.pedido_model import STATUS_APROVADO, STATUS_CANCELADO, STATUS_PENDENTE

# (faturamento mínimo exclusivo, taxa de desconto) — da maior faixa para a menor
FAIXAS_DESCONTO = (
    (10_000, 0.1),
    (5_000, 0.05),
    (1_000, 0.02),
)
CASAS_DECIMAIS = 2


def calcular_desconto(faturamento: float) -> float:
    for limite, taxa in FAIXAS_DESCONTO:
        if faturamento > limite:
            return faturamento * taxa
    return 0


class RelatorioModel:
    def __init__(self, get_connection):
        self._get_connection = get_connection

    def vendas(self) -> dict:
        row = self._get_connection().execute(
            """
            SELECT COUNT(*) AS total_pedidos,
                   SUM(total) AS faturamento,
                   COALESCE(SUM(CASE WHEN status = ? THEN 1 ELSE 0 END), 0) AS pendentes,
                   COALESCE(SUM(CASE WHEN status = ? THEN 1 ELSE 0 END), 0) AS aprovados,
                   COALESCE(SUM(CASE WHEN status = ? THEN 1 ELSE 0 END), 0) AS cancelados
            FROM pedidos
            """,
            (STATUS_PENDENTE, STATUS_APROVADO, STATUS_CANCELADO),
        ).fetchone()

        total_pedidos = row["total_pedidos"]
        faturamento = row["faturamento"] if row["faturamento"] is not None else 0
        desconto = calcular_desconto(faturamento)
        return {
            "total_pedidos": total_pedidos,
            "faturamento_bruto": round(faturamento, CASAS_DECIMAIS),
            "desconto_aplicavel": round(desconto, CASAS_DECIMAIS),
            "faturamento_liquido": round(faturamento - desconto, CASAS_DECIMAIS),
            "pedidos_pendentes": row["pendentes"],
            "pedidos_aprovados": row["aprovados"],
            "pedidos_cancelados": row["cancelados"],
            "ticket_medio": round(faturamento / total_pedidos, CASAS_DECIMAIS) if total_pedidos > 0 else 0,
        }
