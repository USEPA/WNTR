Getting started
======================================

To use WNTR, import the package from within a python console::

	import wntr	

A simple script, getting_started.py, is included in the examples
folder.  This example demonstrates how to:

* Import WNTR
* Generate a WaterNetworkModel 
* Simulate hydraulics
* Plot simulation results on the network

.. literalinclude:: ../../examples/getting_started.py

Additional examples are included in the examples folder.  These examples
include:

==============================  ======================================================
Example File                    Description
==============================  ======================================================
hydraulic_simulators.py         Compare EPANET, Pyomo, and Python hydraulic simulators
water_network_modifications.py  Modify a water network model
simulation_modifications.py	Modify a water network simulation
topographic_metrics.py          Compute topographic resilience metrics
hydrulic_metrics.py             Compute hydraulic resilience metrics
waterquality_metrics.py         Compute water quality resilience metrics
converting_units.py             Convert units
==============================  ======================================================

Several EPANET inp files are included in the examples folder.  These example
network range from a simple 9 node networks to a 13,000 node network.

More advanced case studies are also included in the examples/case studies folder.  These include:

==============================  ======================================================
Case Study                      Description
==============================  ======================================================
Power outage
Pipe break
...
==============================  ======================================================