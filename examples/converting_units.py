from sympy.physics import units

# Convert 12 inches to meters
D = units.convert_to(12*units.inch, units.meter)

# Convert 0.2 mg/L to kg/m3
C = units.convert_to(0.2*units.mg/units.l, units.kg/units.m**3)

# Convert 30 psi to m (assuming density = 1000 kg/m3 and gravity = 9.81 m/s2)
P = 30 * units.psi
P = units.convert_to(P, units.Pa)  # convert psi to pascal
waterpressure = 9810 * units.Pa/units.m
H = P/waterpressure  # convert pascal to m

# Convert 200 gallons/day to m3/day 
if not 'gallon' in units.find_unit('volume'):
    units.gallon = 4*units.quart
R = units.convert_to(200*units.gallon/units.day, units.m**3/units.day)
