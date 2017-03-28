.. _simulation_results:

.. raw:: latex

    \newpage

Simulation results
=============================
WNTR uses Pandas data objects to store simulation results.
The use of Pandas facilitates a comprehensive set of time series analysis options that can be used to evaluate results.
For more information on Pandas, see http://pandas.pydata.org/.

Results are stored in Pandas Panels.  A Panel is a 3-dimensional database. 
One Panel is used to store nodes results and one Panel is used to store link results. 
The Panels are indexed by:

* Node or link attribute

* Time in seconds from the start of the simulation

* Node or link name

Conceptually, Panels can be visualized as blocks of data with 3 axis, as shown in :numref:`fig-panel`.
 
.. _fig-panel:
.. figure:: figures/panel.png
   :scale: 100 %
   :alt: Pandas Panels
   
   Conceptual representation of Panels used to store simulation results.

Node attributes include:

* Demand
* Expected demand
* Leak demand (only when the WNTRSimulator is used)
* Pressure
* Head
* Quality (only when the EpanetSimulator is used for a water quality simulation. Water age, tracer percent, or chemical concentration is stored, depending on the type of water quality analysis)
* Type (junction, tank, or reservoir)
	
Link attributes include:

* Velocity
* Flowrate
* Status (0 indicates closed, 1 indicates open)
* Type (pipe, pump, or valve)

The example **simulation_results.py** demonstrates use cases of simulation results.
Node and link results are accessed using:

.. literalinclude:: ../examples/simulation_results.py
   :lines: 13-14

The indices can be used extract specific information from Panels.
For example, to access the pressure and demand at node '123' at 1 hour:

.. literalinclude:: ../examples/simulation_results.py
   :lines: 17
	
To access the pressure for all nodes and times (the ":" notation returns all variables along the specified axis):  

.. literalinclude:: ../examples/simulation_results.py
   :lines: 20

Attributes can be plotted as a time-series using:
	
.. literalinclude:: ../examples/simulation_results.py
   :lines: 23-24

Attributes can be plotted on the water network model using:
	
.. literalinclude:: ../examples/simulation_results.py
   :lines: 27-30

Panels can be saved to excel files using:

.. literalinclude:: ../examples/simulation_results.py
   :lines: 33-34
