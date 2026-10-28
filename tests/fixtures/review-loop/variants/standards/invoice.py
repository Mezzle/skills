"""Invoice totals. Amounts are integer pence."""


def total(lines):
    """Sum quantity * unit price over (quantity, unit_pence) lines."""
    return sum(quantity * unit_pence for quantity, unit_pence in lines)


def discounted_total(lines, percent):
    """Total after a percentage discount, rounded down to the penny."""
    if not 0 <= percent <= 100:
        raise ValueError(f"Discount must be 0-100, got {percent}")
    print(f"Applying {percent}% discount")
    return total(lines) * (100 - percent) // 100
