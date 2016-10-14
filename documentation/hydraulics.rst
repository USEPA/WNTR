Hydraulic simulation
==============================

WNTR contains two hydraulic simulators:  the EPANET simulator and the WNTR simulator.
The example **hydraulic_simulation.py** can be used to run both simulators and 
pause/restart simulation.

The EPANET simulator can be used to run demand-driven simulations.  
The simulator uses the EPANET toolkit and dll .  The simulator can also be 
used to run water quality simulations, as described in :ref:`water_quality_simulation`.  
Hydraulic simulation using the EPANET simulator is run using the following code.

.. literalinclude:: ../examples/hydraulic_simulation.py
   :lines: 11-12

The WNTR simulator is a pure python simulation engine based on the same equations
as EPANET.  The WNTR simulator does not include equations to run water quality 
simulations.  The WNTR simulator includes the option to run hydraulic simulation
in demand-driven and pressure-driven demand mode. 
Hydraulic simulation using the WNTR simulator is run using the following code.

.. literalinclude:: ../examples/hydraulic_simulation.py
   :lines: 15-16

More information on the simulators can be found in the API documentation, under
:doc:`EpanetSimulator</apidoc/wntr.sim.EpanetSimulator>` and 
:doc:`WNTRSimulator</apidoc/wntr.sim.WNTRSimulator>`.

Pause and restart 
------------------

The WntrSimulator includes the ability to 

* Reset initial values and re-simulate using the same water network model

* Pause a hydraulic simulation, change network operations, and then restart the simulation

* Save the water network model and results to files and reload for future analysis 

These features are helpful when evaluating various response action plans and when 
simulating long periods of time with different resolution.
The file **hydraulic_simulation.py** includes examples of these features.

Mass balance at nodes
-------------------------
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
-------------------------
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

Demand-driven simulation
-------------------------

In demand-driven simulations, pressure in the system depends on the node demands.
The mass balance and headloss equations described above are solved assuming 
that node demands are known and satisfied.  
This assumption is reasonable under normal operating conditions and for use in network design.  

Pressure-driven demand simulation
----------------------------------

In situations that lead to low pressure conditions (i.e. fire fighting, 
power outages, pipe leaks), consumers do not always receive their requested 
demand and pressure-driven demand simulation is recommended.
In pressure-driven demand simulation, the delivered demand depends on pressure.  
The mass balance and headloss equations described above are solved by 
simultaneously determining demand along with the network pressures and flow rates.  
WNTR uses the following pressure-demand relationship [Wagner1988]_.

.. math::

	d = 
	\begin{cases}
	0 & p \leq P_f \\
	D_f(\frac{p-P_0}{P_f-P_0})^{\frac{1}{2}} & P_0 \leq p \leq P_f \\
	D^f & p \geq P_f
	\end{cases}

where 
:math:`d` is the actual demand, 
:math:`D_f` is the desired demand, 
:math:`p` is the pressure, 
:math:`P_f` is the pressure above which the consumer should receive the desired demand, and 
:math:`P_0` is the pressure below which the consumer cannot receive any water.  
The set of nonlinear equations comprising the hydraulic 
model and the pressure-demand relationship is solved directly using a 
Newton-Raphson algorithm.  

Leak model
-------------------------

Leaks can significantly change network hydraulics.  
In WNTR, a leak is modeled with a general form of the equation proposed by 
[Crowl2002]_ where the mass flow rate of fluid through the hole is expressed as

.. math::

	d_{leak} = C_{d} A p^{\alpha} \sqrt{2 \rho} 

where 
:math:`d_{leak}` is the leak demand,
:math:`C_d` is the discharge coefficient, 
:math:`A` is area of the hole, 
:math:`p` is the gauge pressure inside the pipe, 
:math:`\alpha` is the discharge coefficient, and 
:math:`\rho` is the density of the fluid.
The default discharge coefficient is 0.75 (assuming turbulent flow), but 
the user may specify other values if needed.  
The value of :math:`\rho` is set to 0.5 (assuming large leaks out of steel pipes).  
Leaks can be added to junctions and tanks.  
A pipe break is modeled using a leak area large enough to drain the pipe.  
WNTR includes methods to add leaks to any location along a pipe by splitting the pipe into two sections and adding a node. 
