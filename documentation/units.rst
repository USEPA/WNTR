Units
======================================

WNTR is compatible with EPANET inp files using the following unit conventions [Rossman2000]_:

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

* Length = :math:`m`
* Diameter = :math:`m`
* Water pressure = :math:`m`
* Elevation = :math:`m`
* Mass = :math:`kg`
* Time = :math:`s`
* Concentration = :math:`kg/m^3`
* Demand = :math:`m^3/s`
* Velocity = :math:`m/s`
* Acceleration = :math:`g` (1 :math:`g` = 9.81 :math:`m/s^2`)
* Energy = :math:`J`
* Power = :math:`W`
* Pressure = :math:`Pa`
* Mass injection = :math:`kg/s`
* Volume = :math:`m^3`

The sympy package can be used to convert between units.  The example **converting_units.py**
demonstrates its use.

.. literalinclude:: ../examples/converting_units.py
