# Issue 12: discounted invoice totals

Add `discounted_total(lines, percent)` to `invoice.py`.

- Return the invoice total in pence after a percentage discount.
- Round the result down to the nearest penny.
- `percent` is a whole number. Raise `ValueError` if it is outside 0 to 100
  inclusive.
