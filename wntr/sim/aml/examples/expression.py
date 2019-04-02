import aml.aml as aml

x = aml.create_var()
x.value = 2.0
x.lb = -5.0
x.ub = 5.0
print(x.value, x.lb, x.ub)

y = aml.create_var()
y.value = 3.0
expr = x**3 * y
print(expr.evaluate())
print(expr.ad(x, False))
print(expr.ad(y, False))
print(expr.ad2(x, x, False))
print(expr.ad2(x, y, False))
print(expr.ad2(y, y, False))
