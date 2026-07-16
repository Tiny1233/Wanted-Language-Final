import decimal
d = decimal.Decimal

def add(a, b):
    if isinstance(a, int) and isinstance(b, int): return a + b
    return float(d(str(a)) + d(str(b)))
def sub(a, b):
    if isinstance(a, int) and isinstance(b, int): return a - b
    return float(d(str(a)) - d(str(b)))
def mul(a, b):
    if isinstance(a, int) and isinstance(b, int): return a * b
    return float(d(str(a)) * d(str(b)))
def div(a, b):
    if isinstance(a, int) and isinstance(b, int): return a / b
    return float(d(str(a)) / d(str(b)))

