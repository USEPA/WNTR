Units
======================================

WNTR accepts EPANET inp files using the following unit conventions [Rossman2000]_:

* CFS = cubic feet per second
* GPM = gallons per minute
* MGD = million gallons per day
* IMGD = Imperial mgd
* AFD = acre-feet per day
* LPS = liters per second
* LPM = liters per minute
* MLD = million liters per day
* CMH = cubic meters per hour
* CMD = cubic meters per day

Internally, the water network model is converted to SI units 
(Length = m, Mass = kg, Time = s).  
All external data used in the code (i.e. user supplied pressure threshold) should also be in 
SI units. Results are stored in SI units and can be converted to other units if desired.

* Length = m
* Diameter = m
* Water pressure = m
* Elevation = m
* Mass = kg
* Time = s
* Concentration = kg/m3
* Demand = m3/s
* Velocity = m/s
* Energy = J
* Power = W
* Pressure = Pa
* Mass injection = kg/s
* Volume = m3

The sympy package can be used to convert between units.  The example converting_units.py
demonstrates its use.

.. literalinclude:: ../examples/converting_units.py
