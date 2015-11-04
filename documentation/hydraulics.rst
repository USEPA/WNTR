Hydraulic simulation
====================
   
WNTR contains 2 (or 3) simulators...

Epanet simulator (Hydraulic and Water quality)::

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

The following page describes the hydraulic equations used in WNTR.

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
The headloss formula used in WNTR is the Hazen-Williams
formula [Rossman2000]_:

.. math:: H_{n_{j}} - H_{n_{i}} = h_{L} = 10.667 C^{-1.852} d^{-4.871} L q^{1.852}

where :math:`h_{L}` is the headloss in the pipe in meters, :math:`C` is the
Hazen-Williams roughness coefficient (unitless), :math:`d` is the pipe diameter in
meters, :math:`L` is the pipe length in meters, and :math:`q` is the flow rate of
water in the pipe in cubic meters per second. :math:`H_{n_{j}}` is the head
(meters) at the starting node, and :math:`H_{n_{i}}` is the head (meters) at the ending node.

The flow rate in a pipe is positive if water is flowing from
the starting node to the ending node and negative if water is flowing
from the ending node to the starting node. However, this equation is not valid for negative
flow rates. Therefore, WNTR uses a reformulation of this constraint. 

For :math:`q<0`:

.. math:: h_{L} = -10.667 C^{-1.852} d^{-4.871} L |q|^{1.852} 

For :math:`q \geq 0`:

.. math:: h_{L} = 10.667 C^{-1.852} d^{-4.871} L |q|^{1.852}

These equations are symmetric across the origin
and valid for any :math:`q`. Thus, this equation can be used for flow in
either direction. However, the derivative with respect to :math:`q` at :math:`q = 0` 
is :math:`0`. In certain scenarios, this can cause the Jacobian of the
set of hydraulic equations to become singular (when :math:`q=0`). Therefore,
WNTR uses a modified Hazen-Williams formula by default. The modified
Hazen-Williams formula splits the domain of :math:`q` into six segments to
create a piecewise function as presented below.

.. math::

    \frac{h_{L}}{k} &= -|q|^{1.852}                           \hspace{2.5in}      q < -q_{2} \\
    \frac{h_{L}}{k} &= -(a |q|^{3} + b |q|^{2} + c |q| + d)   \hspace{1in}      -q_{2} \leq q \leq -q_{1} \\
    \frac{h_{L}}{k} &= -m |q|                                 \hspace{2.4in}      -q_{1} < q \leq  0 \\
    \frac{h_{L}}{k} &= m |q|                                  \hspace{2.75in}      0 < q < q_{1}  \\
    \frac{h_{L}}{k} &= a |q|^{3} + b |q|^{2} + c |q| + d      \hspace{1.5in}      q_{1} \leq q \leq q_{2} \\
    \frac{h_{L}}{k} &= |q|^{1.852}                            \hspace{2.6in}      q_{2} < q 


where :math:`m`, :math:`q_{1}`, and :math:`q_{2}` are appropriate constants and

.. math:: 

    k = 10.667 C^{-1.852} d^{-4.871} L

The modeling language internally does another reformulation to handle
the absolute values. The result is that flow can be in either
direction and the derivative with respect to :math:`q` is non-zero at all
values of :math:`q`. The two polynomials function to smooth the transition between the other equations, with coefficients chosen so that both function and
gradient values are continuous at :math:`-q_{2}`, :math:`-q_{1}`, :math:`q_{1}`, and
:math:`q_{2}`. The section on smoothing describes this technique in
detail. The two figures below compare
the Hazen-Williams and modified Hazen-Williams curves, with :math:`m = 0.01 m^{2.556}/s^{0.852}`, :math:`C = 100`, :math:`d = 0.5` m, and :math:`L = 200` m. The
figures show that the two formulas are essentially indistinguishable.

Demand-driven analysis
----------------------

Mention adjust demand method


Pressure-driven analysis
--------------------------

Leak model
----------

	
