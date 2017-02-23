.. _water_quality_simulation:

Water quality simulation
==================================

Water quality simulation can only be run using the **EpanetSimulator** using the EPANET 2 Programmer's Toolkit. 
As listed in the :ref:`software_framework` section,  this means that the hydraulic simulation must use demand driven simulation.

.. Note that the WNTRSimulator can be used to compute demands under pressure-driven conditions and those demands can be used in the EPANETSimulator. 
 
Water quality scenarios are defined using the class :meth:`~wntr.scenario.water_quality.Waterquality`.
This class stores information on the water quality type and injection.  
Note that water quality sources defined in the [SOURCES] section of the EPANET INP file will also be simulated.
Reaction parameters in the EPANET INP file will also be applied.
EPANET supports water quality simulation to track chemical concentration, 
water age, and tracer percent.

The example **water_quality_simulation.py** can be used to run water quality simulations and plot results.

The following code can be used to run a hydraulic and water quality simulation, 
in this case, to compute water age.

.. literalinclude:: ../examples/water_quality_simulation.py
   :lines: 7, 20-21

Concentration
-------------
If water quality type is set to 'CHEM', then the EpanetSimulator computes chemical concentration.
The user must supply the injection node(s), source type, quality, and start and end times.
Simulated concentration values at each node are stored in the `quality` section of the node results, described in :ref:`simulation_results`.  

Water age
---------
If water quality type is set to 'AGE', then the EpanetSimulator computes water age.  No other 
input parameters are needed.
Simulated water age values at each node are stored in the `quality` section of the node results, described in :ref:`simulation_results`.  

Tracer
------
If water quality type is set to 'TRACE', then the EpanetSimulator tracks the chemical as a tracer and 
reports the percent of flow originating from a specific location.
The user must supply the injection node(s).
Simulated tracer percent values at each node are stored in the `quality` section of the node results, described in :ref:`simulation_results`.  