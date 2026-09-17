PERCENT_DECIMALS = 2


def calculate_percentage(part: int, total: int) -> float:
    if total == 0:
        return 0
    return round((part / total) * 100, PERCENT_DECIMALS)
