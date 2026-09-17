"""Cálculos numéricos reutilizados pelos relatórios."""

PERCENTAGE_DECIMALS = 2


def calculate_percentage(part: int, total: int) -> float | int:
    """Percentual de `part` sobre `total`, arredondado; 0 quando não há total."""
    if total == 0:
        return 0
    return round((part / total) * 100, PERCENTAGE_DECIMALS)
