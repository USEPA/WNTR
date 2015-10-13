Hydraulic simulation
====================
   
WNTR contains 2 (or 3) simulators...

Epanet simualtor (Hydraulic and Water quality)::

	sim = wntr.sim.EpanetSimulator(wn)
	results = sim.run_sim()

Scipy simulator (Hydraulic only)::

	sim = wntr.sim.ScipySimulator(wn)
	results = sim.run_sim()
	
Pyomo simulator (Hydraulic only)::

	sim = wntr.sim.PyomoSimulator(wn)
	results = sim.run_sim()
	
More information on the simulators can be found in the API documentation, under
:doc:`EpanetSimulator</apidoc/wntr.sim.EpanetSimulator>`, 
:doc:`ScipySimulator</apidoc/wntr.sim.ScipySimulator>`, and 
:doc:`PyomoSimulator</apidoc/wntr.sim.PyomoSimulator>`.

The following page descibes the hydraulic equations used in WNTR.

Mass balence at nodes
----------------------
WNTR uses the same mass balance equations as EPANET [Rossman2000]_. 
Conservation of mass (and the assumption of constant density) requires

.. math::

    \sum_{p \in P_{n}} q_{p,n} - D_{n}^{act} = 0 \hspace{1in} \forall n \in N
    
where 
:math:`P_{n}` is the set of pipes connected to node :math:`n`, 
:math:`q_{p,n}` is the volumetric flow rate of water into node :math:`n` from pipe :math:`p`, 
:math:`D_{n}^{act}` is the actual volumetric demand out of node :math:`n`, and 
:math:`N` is the set of all nodes. 
If water is flowing out of node :math:`n` and into pipe :math:`p`, then 
:math:`q_{p,n}` is negative. Otherwise, it is positive.

Headloss in pipes
---------------------


Demand-driven analysis
----------------------


Pressure-driven analysis
--------------------------

	