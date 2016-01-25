Getting started
======================================

To use WNTR, import the package from within a python console::

	import wntr	

A simple script, **getting_started.py**, is included in the examples
folder.  This example demonstrates how to:

* Import WNTR
* Generate a WaterNetworkModel 
* Simulate hydraulics
* Plot simulation results on the network

.. literalinclude:: ../examples/getting_started.py

Additional examples are included in the examples folder.  These examples
include:

==============================  =========================================================
Example File                    Description
==============================  =========================================================
converting_units.py             Convert units
water_network_model.py  	Generate and modify water network models
networkx_graph.py		Generate a NetworkX graph from a water network model 
hydraulic_simulation.py         Simulate hydraulics using the EPANET and WNTR simulators
water_quality_simualtion.py	Simulate water quality using EPANET
simulation_results.py		Extract information from simulation results
fragility_curve.py		Define and use fragility curves
topographic_metrics.py          Compute topographic resilience metrics
hydraulic_metrics.py            Compute hydraulic resilience metrics
water_quality_metrics.py        Compute water quality resilience metrics
water_security_metrics.py       Compute water security resilience metrics
other_metrics.py       		Compute population impacted and network cost metrics
stochastic_simulation.py	Example running stochastic simualtion
animation.py			Animated network graphics
==============================  =========================================================

Several EPANET inp files are included in the examples/network folder.  Example
network range from a simple 9 node network to a 13,000 node network.

More advanced case studies and demos are also included in the examples/case_studies 
folder and examples/demo folder.  