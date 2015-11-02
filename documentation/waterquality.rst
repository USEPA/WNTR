Water quality simulation
========================

Water quality simulation can be run using the Epanet simualtor.  
A water quality scenario can be defined using the scenario class :doc:`Waterquality</apidoc/wntr.scenario.Waterquality>`.
This class stores information on the water quality type and injection.  
EPANET supports water quality simulation to track chemical concentration, 
water age, and tracer percent.

The following code can be used to run a hydrulic and water quality simulation, 
in this case, to compute water age::

	WQscenario = wntr.scenario.Waterquality('AGE')
	sim = wntr.sim.EpanetSimulator(wn)
	results = sim.run_sim(WQscenario)

Concentration
-------------
If water quality type is set to 'CHEM', then EPANET computes chemical concentration.
The user must supply the injection node(s), source type, quality, start and end time.
Concentration is stored in ``results.node['quality']``.

Water age
---------
If water quality type is set to 'AGE', then EPANET computes water age.  No other 
input parameters are needed.
Water age is stored in ``results.node['quality']``.

Tracer
------
If water quality type is set to 'TRACE', then EPANET tracks the chemical as a tracer and 
reports the percent of flow originating from a specific location.
The user must supply the injection node(s).
Tracer percent is stored in ``results.node['quality']``.