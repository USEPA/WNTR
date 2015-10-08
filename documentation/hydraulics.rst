Hydraulic simulation
====================
   
WNTR contains 2 or 3 simulators...

* Epanet simualtor (Hydraulic and Water quality)
* Scipy simulator (Hydraulic only)
* Pyomo simulator (Hydraulic only)

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


Running a hydraulic simulation
------------------------------
The following code can be used to run a hydrulic simulation using EPANET::

	sim = wntr.sim.EpanetSimulator(wn)
	results = sim.run_sim()
	