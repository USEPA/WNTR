Water network model
======================================

Background from the white paper...

Same components as EPANET with the addition of Leak and more flexible controls

For each section below, add brief explination of methods and EPANET features not supported

For more information, see the :doc:`WaterNetworkModel</apidoc/wntr.network.WaterNetworkModel>` module documentation.

Junctions
---------


Reservoirs
----------
.. note::  When simulating power outages, consider placing check valves next to reservoirs.

Tanks
-----
WNTR assumes tanks are cylindrical. **Non-clyndrical shapes are currently not supported by WNTR.** 


Pipes
-----
.. note:: Pipes with large diameters, large roughness coefficients, and small lengths will have small resistance coefficients. If the resistance coefficient is too small, weird things may happen.

Pumps
-----
.. note::  When simulating power outages, consider placing check bypasses around pumps.


Valves
-------
WNTR supports check valves (CV)and pressure-reducing valves (PRV).  
**Pressure sustaining valvea (PSV), 
pressure breaker valves (PBV),
flow control valves (FCV),
throttle control valves (TCV), and 
general purpose valve (GPV) are currently not supported by WNTR.**

Leaks
-----
Leaks can be added to Junctions and Tanks.  
To add a leak to a Pipe, the pipe must be split, a junction must be added to the water network model, and then a leak can be added.

Curves
------


Patterns
--------


Controls
---------
status


Energy
------


Emitters
--------
Emitters are a form of pressure-dependent demand supported by EPANET. These are used for
devices such as sprinklers where the flow is not controlled by a customer the way a sink or bathtub
faucet is. **Emitters are currently not supported by WNTR.**

Water quality
--------------
quality, source, reactions


Options
-------
time, reaction, options


Coordinates
------------


NetworkX Graph
--------------


Creating a Water Network Model
------------------------------
A water network model can be created from an inp file::

	wn = wntr.network.WaterNetworkModel(inp_file)

Writting an inp file
---------------------
Writes an inp file in SI (LPS) units.
Writes demand pattern associated with Pressure driven simulation.
Does not include features not supported by EPANET.