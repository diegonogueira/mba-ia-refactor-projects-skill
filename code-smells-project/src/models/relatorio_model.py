"""Relatório de vendas: agregações sobre pedidos e regra de desconto por faturamento."""
from src.models.database import get_connection
from src.models.status_pedido import STATUS_APROVADO, STATUS_CANCELADO, STATUS_PENDENTE

# (faturamento mínimo exclusivo, taxa de desconto) — da maior faixa para a menor
FAIXAS_DESCONTO = (
    (10_000, 0.10),
    (5_000, 0.05),
    (1_000, 0.02),
)
CASAS_DECIMAIS = 2


def calcular_desconto(faturamento):
    for limite, taxa in FAIXAS_DESCONTO:
        if faturamento > limite:
            return faturamento * taxa
    return 0


def gerar_relatorio_vendas():
    linha = get_connection().execute(
        """
        SELECT COUNT(*) AS total_pedidos,
               COALESCE(SUM(total), 0) AS faturamento,
               COUNT(CASE WHEN status = ? THEN 1 END) AS pendentes,
               COUNT(CASE WHEN status = ? THEN 1 END) AS aprovados,
               COUNT(CASE WHEN status = ? THEN 1 END) AS cancelados
        FROM pedidos
        """,
        (STATUS_PENDENTE, STATUS_APROVADO, STATUS_CANCELADO),
    ).fetchone()

    total_pedidos, faturamento = linha["total_pedidos"], linha["faturamento"]
    desconto = calcular_desconto(faturamento)
    return {
        "total_pedidos": total_pedidos,
        "faturamento_bruto": round(faturamento, CASAS_DECIMAIS),
        "desconto_aplicavel": round(desconto, CASAS_DECIMAIS),
        "faturamento_liquido": round(faturamento - desconto, CASAS_DECIMAIS),
        "pedidos_pendentes": linha["pendentes"],
        "pedidos_aprovados": linha["aprovados"],
        "pedidos_cancelados": linha["cancelados"],
        "ticket_medio": round(faturamento / total_pedidos, CASAS_DECIMAIS) if total_pedidos > 0 else 0,
    }
