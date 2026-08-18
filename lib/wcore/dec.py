import decimal
d = decimal.Decimal

def isint(n):
    return n == float(n)

def add(a, b):
    if isint(a) and isint(b): return a + b
    return float(d(str(a)) + d(str(b)))
def sub(a, b):
    if isint(a) and isint(b): return a - b
    return float(d(str(a)) - d(str(b)))
def mul(a, b):
    if isint(a) and isint(b): return a * b
    return float(d(str(a)) * d(str(b)))
def div(a, b):
    if isint(a) and isint(b): return a / b
    return float(d(str(a)) / d(str(b)))

def pow(a, b):
    if isint(a) and isint(b): return a ** b
    return float(d(str(a)) ** d(str(b)))



