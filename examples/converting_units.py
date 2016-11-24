from __future__ import division
from past.utils import old_div
from sympy.physics import units

# Convert 12 inches to meters
D = 12*float(old_div(units.inch,units.meter))

# Covert 0.2 mg/L to kg/m3
C = 0.2*float(old_div((old_div(units.mg,units.l)),(old_div(units.kg,units.m**3))))

# Convert 30 psi to m (assuming density = 1000 kg/m3 and gravity = 9.81 m/s2)
if not units.find_unit('waterpressure'):
    units.waterpressure = 9810*units.Pa
P = 30*float(old_div(units.psi,units.waterpressure))

# Convert 200 gallons/day to m3/day 
if not units.find_unit('gallon'):
    units.gallon = 4*units.quart
R = 200*float(old_div(units.gallon,units.m**3)) 