.. raw:: latex

    \newpage

Hydraulic simulation
==============================

WNTR contains two simulators: the **WNTRSimulator** and the **EpanetSimulator**.
See :ref:`software_framework` for more information on features and limitations of these simulators. 

The EpanetSimulator can be used to run demand-driven hydraulic simulations
using the EPANET 2 Programmer's Toolkit.  The simulator can also be 
used to run water quality simulations, as described in :ref:`water_quality_simulation`.  
A hydraulic simulation using the EpanetSimulator is run using the following code.

.. literalinclude:: ../examples/hydraulic_simulation.py
   :lines: 12-13

The WNTRSimulator is a pure Python simulation engine based on the same equations
as EPANET.  The WNTRSimulator does not include equations to run water quality 
simulations.  The WNTRSimulator includes the option to simulate leaks, and run hydraulic simulation
in demand-driven or pressure-driven demand mode.
A hydraulic simulation using the WNTRSimulator is run using the following code.

.. literalinclude:: ../examples/hydraulic_simulation.py
   :lines: 16-17

The example **hydraulic_simulation.py** can be used to run both simulators.

More information on the simulators can be found in the API documentation, under
:meth:`~wntr.sim.epanet.EpanetSimulator` and 
:meth:`~wntr.sim.core.WNTRSimulator`.

Options
----------
Hydraulic simulation options are defined in the :meth:`~wntr.network.model.WaterNetworkOptions` class.
These options include 
duration, 
hydraulic timestep, 
rule timestep, 
pattern timestep, 
pattern start, 
default pattern, 
report timestep, 
report start, 
start clocktime, 
headloss, 
trails, 
accuracy, 
unbalenced, 
demand multiplier, and 
emitter exponent.
All options are used with the EpanetSimulator.  
Options that are not used with the WNTRSimulator are described in :ref:`limitations`.  

Mass balance at nodes
-------------------------
Both simulators uses the mass balance equations from EPANET [Ross00]_:

.. math::

    \sum_{p \in P_{n}} q_{p,n} - D_{n}^{act} = 0 \hspace{1in} \forall n \in N
    
where 
:math:`P_{n}` is the set of pipes connected to node :math:`n`, 
:math:`q_{p,n}` is the flow rate of water into node :math:`n` from pipe :math:`p` (m³/s), 
:math:`D_{n}^{act}` is the actual demand out of node :math:`n` (m³/s), and 
:math:`N` is the set of all nodes. 
If water is flowing out of node :math:`n` and into pipe :math:`p`, then 
:math:`q_{p,n}` is negative. Otherwise, it is positive.

Headloss in pipes
-------------------------
Both simulators use the Hazen-Williams headloss formula from EPANET [Ross00]_:

.. math:: H_{n_{j}} - H_{n_{i}} = h_{L} = 10.667 C^{-1.852} d^{-4.871} L q^{1.852}

where 
:math:`h_{L}` is the headloss in the pipe (m), 
:math:`C` is the Hazen-Williams roughness coefficient (unitless), 
:math:`d` is the pipe diameter (m), 
:math:`L` is the pipe length (m),  
:math:`q` is the flow rate of water in the pipe (m³/s),
:math:`H_{n_{j}}` is the head at the starting node (m), and 
:math:`H_{n_{i}}` is the head at the ending node (m).

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
set of hydraulic equations to become singular (when :math:`q=0`). The WNTRSimulator
uses a modified Hazen-Williams formula. The modified
Hazen-Williams formula splits the domain of :math:`q` into six segments to
create a piecewise smooth function.

.. as presented below.

	.. math::

		\frac{h_{L}}{k} &= -|q|^{1.852}                           \hspace{2.5in}      q < -q_{2} \\
		\frac{h_{L}}{k} &= -(a |q|^{3} + b |q|^{2} + c |q| + d)   \hspace{1in}      -q_{2} \leq q \leq -q_{1} \\
		\frac{h_{L}}{k} &= -m |q|                                 \hspace{2.4in}      -q_{1} < q \leq  0 \\
		\frac{h_{L}}{k} &= m |q|                                  \hspace{2.75in}      0 < q < q_{1}  \\
		\frac{h_{L}}{k} &= a |q|^{3} + b |q|^{2} + c |q| + d      \hspace{1.5in}      q_{1} \leq q \leq q_{2} \\
		\frac{h_{L}}{k} &= |q|^{1.852}                            \hspace{2.6in}      q_{2} < q 


	where 
	:math:`m` is 0.001,
	:math:`q_{1}` is 0.0002,  
	:math:`q_{2}` is 0.0004,
	a = (2*(f1-f2) - (q1-q2)*(df2+df1))/(q2**3-q1**3+3*q1*q2*(q1-q2))
	b = (df1 - df2 + 3*(q2**2-q1**2)*a)/(2*(q1-q2))
	c = df2 - 3*q2**2*a - 2*q2*b
	d = f2 - q2**3*a - q2**2*b - q2*c
	f1 = m* q1
	f2 =q2**1.852
	df1 = m
	df2 = 1.852* q2**0.852

	.. math:: 

		k = 10.667 C^{-1.852} d^{-4.871} L

	Internally, these equations are reformulation to handle absolute values. 
	The result is that flow can be in either
	direction and the derivative with respect to :math:`q` is non-zero at all
	values of :math:`q`. The two polynomials function to smooth the transition between the other equations, with coefficients chosen so that both function and
	gradient values are continuous at :math:`-q_{2}`, :math:`-q_{1}`, :math:`q_{1}`, and
	:math:`q_{2}`. 
	
Demand-driven simulation
-------------------------

In demand-driven simulation, pressure in the system depends on the node demands.
The mass balance and headloss equations described above are solved assuming 
that node demands are known and satisfied.  
This assumption is reasonable under normal operating conditions and for use in network design.  
Both simulators can run hydraulics using demand-driven simulation.

Pressure-driven demand simulation
----------------------------------

In situations that lead to low pressure conditions (i.e., fire fighting, 
power outages, pipe leaks), consumers do not always receive their requested 
demand and pressure-driven demand simulation is recommended.
In pressure-driven demand simulation, the delivered demand depends on pressure.  
The mass balance and headloss equations described above are solved by 
simultaneously determining demand along with the network pressures and flow rates.  

The WNTRSimulator can run hydraulics using pressure-driven demand simulation
using the following pressure-demand relationship [WaSM88]_:

.. math::

	d = 
	\begin{cases}
	0 & p \leq P_0 \\
	D_f(\frac{p-P_0}{P_f-P_0})^{\frac{1}{2}} & P_0 \leq p \leq P_f \\
	D^f & p \geq P_f
	\end{cases}

where 
:math:`d` is the actual demand (m³/s), 
:math:`D_f` is the desired demand (m³/s), 
:math:`p` is the pressure (Pa), 
:math:`P_f` is the pressure above which the consumer should receive the desired demand (Pa), and 
:math:`P_0` is the pressure below which the consumer cannot receive any water (Pa).  
The set of nonlinear equations comprising the hydraulic 
model and the pressure-demand relationship is solved directly using a 
Newton-Raphson algorithm.  

:numref:`fig-pressure-driven` illustrates the pressure demand relationship using demand-driven and pressure-driven demand simulation.
In the example, 
:math:`D_f` is 0.0025 m³/s (39.6 GPM),
:math:`P_f` is 200,000 Pa (29.0 psi), and 
:math:`P_0` is 25,000 Pa (3.6 psi).
Using demand-driven simulation, the demand is equal to :math:`D_f` regardless of pressure.  
Using pressure-driven demand simulation, the demand starts to decrease when pressure is below :math:`P_f` and goes to 0 when pressure is below :math:`P_0`.

.. _fig-pressure-driven:
.. figure:: figures/pressure_driven.png
   :scale: 100 %
   :alt: Pressure driven example
   
   Example relationship between pressure and demand using demand-driven and pressure-driven demand simulation.

Leak model
-------------------------

The WNTRSimulator includes the ability to add leaks to the network.
The leak is modeled with a general form of the equation proposed by 
[CrLo02]_ where the mass flow rate of fluid through the hole is expressed as:

.. math::

	d_{leak} = C_{d} A p^{\alpha} \sqrt{\frac{2}{\rho}}

where 
:math:`d_{leak}` is the leak demand (m³/s),
:math:`C_d` is the discharge coefficient (unitless), 
:math:`A` is the area of the hole (m²), 
:math:`p` is the gauge pressure inside the pipe (Pa), 
:math:`\alpha` is the discharge coefficient, and 
:math:`\rho` is the density of the fluid.
The default discharge coefficient is 0.75 (assuming turbulent flow), but 
the user can specify other values if needed.  
The value of :math:`\alpha` is set to 0.5 (assuming large leaks out of steel pipes).  
Leaks can be added to junctions and tanks.  
A pipe break is modeled using a leak area large enough to drain the pipe.  
WNTR includes methods to add leaks to any location along a pipe by splitting the pipe into two sections and adding a node. 

:numref:`fig-leak` illustrates leak demand.
In the example, the leak diameter is set to 0.5 cm, 1.0 cm, and 1.5 cm. 

.. _fig-leak:
.. figure:: figures/leak_demand.png
   :scale: 100 %
   :alt: Leak demand
   
   Example relationship between leak demand and pressure.


Pause and restart 
------------------

The WNTRSimulator includes the ability to 

* Reset initial values and re-simulate using the same water network model.  Initial values include tank head, reservoir head, pipe status, pump status, and valve status.

* Pause a hydraulic simulation, change network operations, and then restart the simulation

* Save the water network model and results to files and reload for future analysis 

These features are helpful when evaluating various response action plans or when 
simulating long periods of time where the time resolution might vary.
The file **hydraulic_simulation.py** includes examples of these features.
