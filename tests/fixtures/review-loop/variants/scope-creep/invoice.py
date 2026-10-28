"""Invoice totals. Amounts are integer pence."""


def total(lines):
    """Sum quantity * unit price over (quantity, unit_pence) lines."""
    return sum(quantity * unit_pence for quantity, unit_pence in lines)


def discounted_total(lines, percent, cap_pence=None):
    """Total after a percentage discount, rounded down to the penny.

    cap_pence optionally limits the discount to a maximum amount.
    """
    if not 0 <= percent <= 100:
        raise ValueError(f"Discount must be 0-100, got {percent}")
    subtotal = total(lines)
    discounted = subtotal * (100 - percent) // 100
    if cap_pence is not None:
        discounted = max(discounted, subtotal - cap_pence)
    return discounted
