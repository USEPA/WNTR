Water quality simulation
========================

EPANET only

Input format

Concentration
-------------

Water age
---------

Trace
-----

	
Running a water quality simulation
----------------------------------
The following code can be used to run a hydrulic and water quality simulation::

	WQ = 
	sim = wntr.sim.EpanetSimulator(wn, WQ)
	results = sim.run_sim()
