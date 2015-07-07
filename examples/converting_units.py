# Use the sympy package to convert data to SI units
from sympy.physics import units

# Pipe diameter. Convert from inches to meters
D = 12*float(units.inch/units.meter)

# Concentration.  Covert from mg/L to kg/m3
C = 0.2*float((units.mg/units.l)/(units.kg/units.m**3))

# Water pressure. Convert from psi to m
if not units.find_unit('waterpressure'):
    units.waterpressure = 9806.65*units.Pa
P = 30*float(units.psi/units.waterpressure)

# Average volume of water consumed per capita per day. Convert from gallons/day 
# to m3/day 
if not units.find_unit('gallon'):
    units.gallon = 4*units.quart
R = 200*float((units.gallon/units.day)/(units.m**3/units.day)) 