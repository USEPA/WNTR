Getting started
======================================

WNTR can be run from a Python console, or using an Interactive Development Environment (IDE), like Spyder.
To start using WNTR, import the package ::

	import wntr	

A simple script, **getting_started.py**, is included in the examples
folder.  This example demonstrates how to:

* Import WNTR
* Generate a water network model 
* Simulate hydraulics
* Plot simulation results on the network

.. literalinclude:: ../examples/getting_started.py

Additional examples are included in the examples folder.  These examples
include:

==============================  =========================================================================================================
Example File                    Description
==============================  =========================================================================================================
converting_units.py             Convert units
water_network_model.py  	Generate and modify water network models
networkx_graph.py			Generate a NetworkX graph from a water network model 
hydraulic_simulation.py		Simulate hydraulics using the EPANET and WNTR simulators
water_quality_simulation.py	Simulate water quality using EPANET
simulation_results.py		Extract information from simulation results
disaster_scenarios.py		Define disaster scenarios, including power outage, pipe leak, and changes to supply and demand
resilience_metrics.py           Compute resilience metrics, including topographic, hydraulic, water quality and water security metrics
stochastic_simulation.py	Run a stochastic simulation
fragility_curves.py		Define fragility curves
parallel_simulations.py		Run simulations in parallel
animation.py			Animate network graphics
==============================  =========================================================================================================

Several EPANET inp files are included in the examples/network folder.  Example
network range from a simple 9 node network to a 3,000 node network.
Ipython demos are included in the examples/demo folder. 
Additional network models can be downloaded from the University of Kentucky 
Water Distribution System Research Database at
http://www.uky.edu/WDST/database.html.
