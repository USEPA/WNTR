Water network model
======================================

The water network model includes the pipe network, controls, ...
This is similar to the model components stored in an EPANET inp file.
Some EPANET features are not supported by WNTR, as described below.
WNTR also includes features that are not supported by EPANET, 
including leaks, pressure-driven hydraulic simulation, and 
more flexible controls.

WNTR is compatible with EPANET inp files [Rossman2000]_.  
A water network model can be created directly from an inp file or 
by adding individual components to generate a network representation::

	wn = wntr.network.WaterNetworkModel(inp_file)

The water network model can also be written to inp file.
Files are written in LPS units.
The demands associated with pressure-driven simulation can be stored in the file.
The inp file writer does not include features not supported by EPANET::

	wn.write_inpfile(inp_file)

For more information on the water network model, see the 
:doc:`WaterNetworkModel</apidoc/wntr.network.WaterNetworkModel>` 
module documentation.

The following page describes water network model components.  
EPANET components that are not supported by WNTR are noted.

Junctions
---------


Reservoirs
----------
.. note::  When simulating power outages, consider placing check valves next to reservoirs.

Tanks
-----
WNTR assumes tanks are cylindrical. **Non-cylindrical shapes are currently not supported by WNTR.** 


Pipes
-----
.. note:: Pipes with large diameters, large roughness coefficients, and small lengths will have small resistance coefficients. If the resistance coefficient is too small, weird things may happen.

Pumps
-----
.. note::  When simulating power outages, consider placing check bypasses around pumps.


Valves
-------
WNTR supports check valves (CV) and pressure-reducing valves (PRV).  
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
stored in the graph

