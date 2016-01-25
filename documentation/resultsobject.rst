.. _simulation_results:

Simulation results
====================
Simulation results are stored in Pandas Panels.  
For more information on Pandas, see http://pandas.pydata.org/.
The example **simulation_results.py** includes examples using simualtion results.
Results are stored in one Panel for nodes and one Panel for links, accessed using :: 

.. literalinclude:: ../examples/simulation_results.py
   :lines: 12-13

Each Panel is indexed by item, major_axis, and minor_axis.

* item
    For node panels: 
	* demand
	* expected_demand
	* leak_demand (only when the ScipySimulator is used)
	* pressure
	* head
	* quality (only when the EpanetSimulator is used for a water quality simuation)
	* type
    
    For link panels: 
	* velocity
	* flowrate
	* type
	
* major_axis
	Time in seconds from the start of the simulation
	
* minor_axis
    For node panels: 
	* node name
	
    For link panels: 
	* link name

For example, to access the pressure and demand at node '123' at 1 hour, use the following code::

.. literalinclude:: ../examples/simulation_results.py
   :lines: 16
	
To access the pressure for all nodes and times, use the following code::

.. literalinclude:: ../examples/simulation_results.py
   :lines: 19

Attributes can be plotted on the water network model using::
	
.. literalinclude:: ../examples/simulation_results.py
   :lines: 22-24

Attributes can be plotted as a time-series using::
	
.. literalinclude:: ../examples/simulation_results.py
   :lines: 27-28

Panels can be saved to excel files using the following code::

.. literalinclude:: ../examples/simulation_results.py
   :lines: 31-32
