from sympy.physics import units

# Convert 12 inches to meters
D = 12*float(units.inch/units.meter)

# Covert 0.2 mg/L to kg/m3
C = 0.2*float((units.mg/units.l)/(units.kg/units.m**3))

# Convert 30 psi to m (assuming density = 1000 kg/m3 and gravity = 9.81 m/s2)
if not units.find_unit('waterpressure'):
    units.waterpressure = 9810*units.Pa
P = 30*float(units.psi/units.waterpressure)

# Convert 200 gallons/day to m3/day 
if not units.find_unit('gallon'):
    units.gallon = 4*units.quart
R = 200*float(units.gallon/units.m**3) 