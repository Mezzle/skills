"""Invoice totals. Amounts are integer pence."""


def total(lines):
    """Sum quantity * unit price over (quantity, unit_pence) lines."""
    return sum(quantity * unit_pence for quantity, unit_pence in lines)


def discounted_total(lines, percent):
    """Total after a percentage discount, rounded down to the penny."""
    return total(lines) * (100 - percent) // 100
