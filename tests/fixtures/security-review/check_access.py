"""Independent fixture oracle, also available to the evaluated agent."""
from app import read_document

assert read_document('alice', 'alice-note') == 'Alice private note'
try:
    read_document('alice', 'bob-note')
except PermissionError:
    pass
else:
    raise AssertionError('Cross-tenant access was allowed')
print('Legitimate access passes; cross-tenant access denied.')
